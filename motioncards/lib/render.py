#!/usr/bin/env python3
"""Render MotionCards scenes to PNG frames through the real sandboxed host protocol.

This is the visual feedback loop for authors and AI agents: compile each scene exactly as the
packager does (loopback preview origin), load it in a sandboxed iframe, seek the authoritative
timeline to several timestamps and screenshot the stage at phone and tablet framing.  It also
fails on any runtime error reported by the card, so a broken card is caught before upload.

Requires the optional Python package ``playwright`` and a Chromium build.  Set
MOTIONCARDS_CHROMIUM to an explicit Chromium executable when the bundled one is unavailable.
"""
from __future__ import annotations
import os
from pathlib import Path
from .compiler import compile_scene,validate_scene

ORIGIN="http://127.0.0.1:8767"
HOST_URL=ORIGIN+"/motioncards-render-host.html"
CHANNEL="0123456789abcdef0123456789abcdef0123"
# Same policy the production MotionCards Worker sends with every entry (motioncards-worker/worker.mjs),
# with the loopback render host as the allowed frame ancestor.
ENTRY_CSP="; ".join(["default-src 'none'","script-src 'unsafe-inline'","style-src 'unsafe-inline'","img-src data:","font-src 'none'",
    "connect-src 'none'","media-src 'none'","object-src 'none'","frame-src 'none'","worker-src 'none'","form-action 'none'","base-uri 'none'",
    "frame-ancestors "+ORIGIN,"sandbox allow-scripts"])
# Approximate inner stage sizes of the Kafu host player (see app/modules/motioncards.css).
SIZES={"phone":(340,360),"tablet":(600,480)}

HOST_HTML="""<!doctype html><meta charset=utf-8><style>html,body{margin:0;background:#fff}iframe{border:0;display:block}</style>
<body><iframe sandbox="allow-scripts" title="MotionCards render"></iframe>
<script>
let frame=document.querySelector('iframe'),port=null,pending=null;window.mcErrors=[];window.mcReady=false;
window.mcSize=(w,h)=>{frame.style.width=w+'px';frame.style.height=h+'px';};
window.mcLoad=(src,qid,w,h)=>{window.mcQid=qid;window.mcReady=false;port=null;const f=document.createElement('iframe');f.setAttribute('sandbox','allow-scripts');f.title='MotionCards render';frame.replaceWith(f);frame=f;mcSize(w,h);frame.src=src+'#'+'"""+CHANNEL+"""';};
window.mcSeek=ms=>new Promise((res,rej)=>{pending={ms,res,rej};port.postMessage({type:'seek',protocol:1,channel_id:'"""+CHANNEL+"""',qid:window.mcQid,time_ms:ms});setTimeout(()=>rej(new Error('seek_timeout')),4000);});
addEventListener('message',ev=>{const m=ev.data;if(ev.source!==frame.contentWindow||!m||m.type!=='kafu-motioncards-ready')return;
 const ch=new MessageChannel();port=ch.port1;port.onmessage=e=>{const x=e.data;
  if(x.type==='ready')window.mcReady=true;
  else if(x.type==='error'){window.mcErrors.push('card reported render error');if(pending)pending.rej(new Error('card_error'));}
  else if((x.type==='state'||x.type==='ended')&&pending&&x.time_ms===pending.ms){const p=pending;pending=null;p.res(x.type);}
 };port.start();frame.contentWindow.postMessage({type:'connect',protocol:1,channel_id:'"""+CHANNEL+"""',qid:window.mcQid},'*',[ch.port2]);});
</script>"""

def _launch(p):
    exe=os.environ.get("MOTIONCARDS_CHROMIUM")
    return p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()

def _explain(errors:list)->str:
    own=[e.replace("motioncards error: ","") for e in errors if "motioncards error" in e]
    return (own or errors or ["no error message was captured"])[0]

def _router(html:str,qid:str,blocked:list):
    entry=ORIGIN+"/"+qid+".html"
    def route(r):
        url=r.request.url
        if url==HOST_URL:r.fulfill(status=200,content_type="text/html",body=HOST_HTML);return
        if url.split("#")[0]==entry:r.fulfill(status=200,content_type="text/html",headers={"Content-Security-Policy":ENTRY_CSP},body=html);return
        blocked.append(url);r.abort()
    return route

def default_times(duration:int,frames:int)->list[int]:
    frames=max(2,min(24,frames))
    return sorted({round(duration*i/(frames-1)) for i in range(frames)})

def render_scenes(scenes:list[dict],out:Path,times:list[int]|None=None,frames:int=6,sizes:list[str]|None=None,sheet:bool=True)->list[dict]:
    """Render each scene; returns a report per scene.  Raises RuntimeError on any card error."""
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True,exist_ok=True)
    sizes=sizes or ["phone","tablet"]
    reports=[]
    with sync_playwright() as p:
        browser=_launch(p)
        try:
            for scene in scenes:
                qid=str(scene["qid"]);duration=int(scene["duration_ms"]);validate_scene(scene,qid,duration)
                html=compile_scene(scene,[ORIGIN],preview=True)
                stamps=times or default_times(duration,frames)
                ctx=browser.new_context(device_scale_factor=2)
                blocked=[]
                ctx.route("**/*",_router(html,qid,blocked))
                page=ctx.new_page();errors=[];notes=[]
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("console",lambda m:errors.append(m.text) if m.type=="error" else (notes.append(m.text) if "motioncards" in m.text else None))
                page.goto(HOST_URL)
                files=[]
                for size in sizes:
                    w,h=SIZES[size]
                    page.set_viewport_size({"width":w,"height":h})
                    page.evaluate("([s,q,w,h])=>mcLoad(s,q,w,h)",[ORIGIN+"/"+qid+".html",qid,w,h])
                    try:page.wait_for_function("window.mcReady===true||window.mcErrors.length>0",timeout=8000)
                    except Exception:raise RuntimeError(f"{qid}: card never became ready; "+_explain(errors)) from None
                    if page.evaluate("window.mcErrors.length"):raise RuntimeError(f"{qid}: "+_explain(errors))
                    for t in stamps:
                        try:page.evaluate("ms=>mcSeek(ms)",t)
                        except Exception:raise RuntimeError(f"{qid}: failed at t={t} ms; "+_explain(errors)) from None
                        f=out/f"{qid}_{size}_{t:05d}ms.png"
                        page.locator("iframe").screenshot(path=str(f))
                        files.append(str(f))
                    # Seeking backwards must reproduce exactly the same frame (deterministic timeline).
                    # Compared on the rendered DOM (exact, not subject to paint timing).
                    frame=page.frames[-1]
                    snap=lambda:frame.evaluate("()=>{const c=document.getElementById('stage').cloneNode(true);c.querySelectorAll('[display=\"none\"],[style*=\"display: none\"],[style*=\"display:none\"]').forEach(e=>e.remove());return c.outerHTML}")
                    for mid in sorted({stamps[len(stamps)//2],stamps[-1]}):
                        page.evaluate("ms=>mcSeek(ms)",stamps[-1]);page.evaluate("ms=>mcSeek(ms)",mid);again=snap()
                        page.evaluate("ms=>mcSeek(ms)",stamps[0]);page.evaluate("ms=>mcSeek(ms)",mid)
                        if snap()!=again:raise RuntimeError(f"{qid}: frame at {mid} ms differs depending on the previous frame; render(t) must compute everything from t, not accumulate state")
                errs=[e for e in errors if "favicon" not in e]
                if errs or blocked:raise RuntimeError(f"{qid}: runtime errors {errs[:3]} blocked {blocked[:3]}")
                ctx.close()
                report={"qid":qid,"frames":files,"times_ms":stamps,"sizes":sizes,"notes":sorted(set(notes))}
                if sheet:
                    s=_contact_sheet(files,out/f"{qid}_sheet.png",len(stamps))
                    if s:report["sheet"]=s
                reports.append(report)
        finally:
            browser.close()
    return reports

def _contact_sheet(files:list[str],target:Path,per_row:int):
    try:from PIL import Image,ImageDraw
    except ImportError:return None
    imgs=[Image.open(f).convert("RGB") for f in files]
    rows=[imgs[i:i+per_row] for i in range(0,len(imgs),per_row)]
    pad=12;label=22
    width=max(sum(i.width for i in r)+pad*(len(r)+1) for r in rows)
    height=sum(max(i.height for i in r)+pad+label for r in rows)+pad
    sheet=Image.new("RGB",(width,height),(236,240,241));draw=ImageDraw.Draw(sheet);y=pad
    k=0
    for r in rows:
        x=pad
        for im in r:
            name=Path(files[k]).stem.split("_",1)[1];k+=1
            draw.text((x,y),name,fill=(40,60,66));sheet.paste(im,(x,y+label));x+=im.width+pad
        y+=max(i.height for i in r)+label+pad
    sheet.save(target);return str(target)
