from __future__ import annotations
import json,re
from .spec import PROTOCOL_VERSION,RUNTIME_VERSION,validate_duration,QID_RE

UNSAFE_CUSTOM=re.compile(r"\b(eval|Function|fetch|XMLHttpRequest|WebSocket|EventSource|Worker|SharedWorker|setTimeout|setInterval|requestAnimationFrame|document\.|localStorage|sessionStorage|indexedDB|window\.open|location\s*=)\b")

def _validate_scene_v2(scene:dict,qid:str,duration_ms:int):
    from .engine_v2 import validate_scene_v2
    if scene.get("qid")!=qid or not QID_RE.fullmatch(str(qid)):raise ValueError("scene_qid_mismatch")
    if scene.get("duration_ms")!=duration_ms:raise ValueError("scene_duration_mismatch")
    validate_duration(duration_ms)
    takeaway=scene.get("takeaway")
    if not isinstance(takeaway,str) or not takeaway.strip() or len(takeaway.strip())>240:raise ValueError("takeaway_invalid")
    if takeaway.strip().upper().startswith("EDIT:"):raise ValueError("takeaway_unfinished_placeholder")
    if "replace" in scene and not isinstance(scene["replace"],bool):raise ValueError("replace_intent_must_be_boolean")
    return validate_scene_v2(scene,duration_ms)

def validate_scene(scene:dict,qid:str,duration_ms:int):
    # Schema v2 (engine_v2.py) is opt-in per scene; schema v1 below is frozen byte-for-byte.
    if isinstance(scene,dict) and scene.get("schema_version")==2:return _validate_scene_v2(scene,qid,duration_ms)
    if not isinstance(scene,dict) or scene.get("schema_version")!=1:raise ValueError("scene_schema_unsupported")
    if scene.get("qid")!=qid or not QID_RE.fullmatch(str(qid)):raise ValueError("scene_qid_mismatch")
    if scene.get("duration_ms")!=duration_ms:raise ValueError("scene_duration_mismatch")
    validate_duration(duration_ms)
    takeaway=str(scene.get("takeaway") or "").strip()
    if not takeaway or len(takeaway)>240:raise ValueError("takeaway_invalid")
    if takeaway.upper().startswith("EDIT:"):raise ValueError("takeaway_unfinished_placeholder")
    if "replace" in scene and not isinstance(scene["replace"],bool):raise ValueError("replace_intent_must_be_boolean")
    layers=scene.get("layers")
    if not isinstance(layers,list) or not 1<=len(layers)<=80:raise ValueError("layers_invalid")
    allowed={"label","rect","circle","arrow","path","highlight","focus"}
    for layer in layers:
        if not isinstance(layer,dict) or layer.get("type") not in allowed:raise ValueError("layer_type_invalid")
        start=int(layer.get("start_ms",0));end=int(layer.get("end_ms",duration_ms))
        if start<0 or end<start or end>duration_ms:raise ValueError("layer_timing_invalid")
        if layer.get("type")=="label" and len(str(layer.get("text") or ""))>120:raise ValueError("label_too_long")
        if layer.get("type")=="path" and len(str(layer.get("d") or ""))>2000:raise ValueError("path_too_long")
    custom=scene.get("custom_renderer")
    if custom is not None:
        if not isinstance(custom,str) or len(custom)>12000 or UNSAFE_CUSTOM.search(custom):raise ValueError("custom_renderer_unsafe")
        if "function renderCustom(" not in custom:raise ValueError("custom_renderer_contract")
    return scene

RUNTIME_JS=r"""
const hashChannel=location.hash.slice(1);
if(!/^[a-f0-9]{36}$/.test(hashChannel))throw new Error('motioncards_channel_invalid');
CONFIG.channel_id=hashChannel;
const MC={protocol:1,qid:CONFIG.qid,duration:CONFIG.duration_ms,port:null,destroyed:false};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const lerp=(a,b,p)=>a+(b-a)*p;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function state(layer,t){
  const a=layer.from||{},b=layer.to||a,s=Number(layer.start_ms||0),e=Number(layer.end_ms??CONFIG.duration_ms);
  const p=e===s?(t>=e?1:0):clamp((t-s)/(e-s),0,1),out={};
  for(const k of new Set([...Object.keys(a),...Object.keys(b)])){const x=a[k],y=b[k];out[k]=(typeof x==='number'&&typeof y==='number')?lerp(x,y,p):(p<1?(x??y):(y??x));}
  out.opacity=(t<s||t>e)?0:Number(out.opacity??layer.opacity??1);return out;
}
function common(st){return ' opacity="'+clamp(Number(st.opacity??1),0,1)+'" transform="translate('+Number(st.x||0)+' '+Number(st.y||0)+') rotate('+Number(st.rotate||0)+') scale('+Number(st.scale||1)+')"';}
function renderLayer(l,t){
 const s=state(l,t),stroke=esc(l.stroke||'#18363a'),fill=esc(l.fill||'none'),w=Number(l.stroke_width||3),cm=common(s);
 if(l.type==='label')return '<text x="'+Number(l.x||0)+'" y="'+Number(l.y||0)+'"'+cm+' fill="'+esc(l.color||'#18363a')+'" font-size="'+Number(l.size||24)+'" font-weight="'+esc(l.weight||'600')+'" text-anchor="'+esc(l.anchor||'middle')+'">'+esc(l.text||'')+'</text>';
 if(l.type==='rect'||l.type==='highlight'||l.type==='focus')return '<rect x="'+Number(l.x||0)+'" y="'+Number(l.y||0)+'" width="'+Number(l.width||100)+'" height="'+Number(l.height||60)+'" rx="'+Number(l.rx||12)+'"'+cm+' fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+w+'"/>';
 if(l.type==='circle')return '<circle cx="'+Number(l.cx||0)+'" cy="'+Number(l.cy||0)+'" r="'+Number(l.r||20)+'"'+cm+' fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+w+'"/>';
 if(l.type==='path')return '<path d="'+esc(l.d||'')+'"'+cm+' fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+w+'" stroke-linecap="round" stroke-linejoin="round"/>';
 if(l.type==='arrow'){const x1=Number(l.x1||0),y1=Number(l.y1||0),x2=Number(l.x2||0),y2=Number(l.y2||0),dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len,px=-uy,py=ux,back=14,wing=8,bx=x2-ux*back,by=y2-uy*back,p1=(bx+px*wing)+' '+(by+py*wing),p2=(bx-px*wing)+' '+(by-py*wing);return '<g'+cm+'><line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="'+stroke+'" stroke-width="'+w+'" stroke-linecap="round"/><path d="M '+x2+' '+y2+' L '+p1+' L '+p2+' Z" fill="'+stroke+'"/></g>';}
 return '';
}
function renderAt(ms){
 const t=clamp(Number(ms)||0,0,CONFIG.duration_ms);art.innerHTML=CONFIG.layers.map(l=>renderLayer(l,t)).join('');
 if(typeof renderCustom==='function')renderCustom(art,t,{clamp,lerp,esc,CONFIG});
 time.textContent=(t/1000).toFixed(1)+'s';root.dataset.ended=t>=CONFIG.duration_ms?'1':'0';
}
function valid(m){return m&&m.protocol===1&&m.channel_id===CONFIG.channel_id&&m.qid===CONFIG.qid;}
addEventListener('message',ev=>{
 if(ev.source!==parent||!CONFIG.allowed_host_origins.includes(ev.origin))return;
 const m=ev.data;if(!m||m.type!=='connect'||!valid(m)||!ev.ports?.[0]||MC.port)return;
 MC.port=ev.ports[0];MC.port.onmessage=e=>{
   const x=e.data;if(!valid(x)||MC.destroyed)return;
   if(x.type==='tick'||x.type==='seek'){renderAt(x.time_ms);MC.port.postMessage({type:x.time_ms>=CONFIG.duration_ms?'ended':'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:clamp(Number(x.time_ms)||0,0,CONFIG.duration_ms)});}
   else if(x.type==='restart'){renderAt(0);MC.port.postMessage({type:'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:0});}
   else if(x.type==='play'||x.type==='pause'){MC.port.postMessage({type:'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:Number(x.time_ms)||0,playing:x.type==='play'});}
   else if(x.type==='destroy'){MC.destroyed=true;MC.port.close();}
 };
 MC.port.start();MC.port.postMessage({type:'ready',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,duration_ms:CONFIG.duration_ms});
});
renderAt(0);
parent.postMessage({type:'kafu-motioncards-ready',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid},'*');
"""

def _validate_host_origins(allowed:list[str],preview:bool=False):
    if not allowed:raise ValueError("allowed_host_origin_invalid")
    production=re.compile(r"https://[A-Za-z0-9.-]+(?::\d+)?$")
    loopback=re.compile(r"http://(?:127\.0\.0\.1|localhost)(?::[1-9]\d{0,4})?$")
    for origin in allowed:
        if production.fullmatch(origin):continue
        if preview and loopback.fullmatch(origin):continue
        raise ValueError("allowed_host_origin_invalid")
    return allowed

def compile_scene(scene:dict,allowed_host_origins:list[str]|None=None,preview:bool=False,voice:bytes|None=None)->str:
    qid=str(scene["qid"]);duration=int(scene["duration_ms"]);validate_scene(scene,qid,duration)
    allowed=_validate_host_origins(allowed_host_origins or ["https://kafu.blsmohamme97.workers.dev"],preview)
    if scene.get("schema_version")==2:
        from .engine_v2 import compile_scene_v2
        html=compile_scene_v2(scene,allowed,RUNTIME_VERSION)
        if voice is None:return html
        from .voice import embed_voice
        return embed_voice(html,voice)
    if voice is not None:raise ValueError("voice_requires_schema_v2")
    cfg={"qid":qid,"duration_ms":duration,"layers":scene["layers"],"channel_id":"","allowed_host_origins":allowed,"runtime_version":RUNTIME_VERSION}
    custom=scene.get("custom_renderer") or "function renderCustom(){}"
    cfgtext=json.dumps(cfg,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;background:#f7fbfb;color:#18363a;font-family:system-ui,sans-serif}#root{height:100%;display:grid;grid-template-rows:1fr auto;overflow:hidden}svg{width:100%;height:100%;display:block}#time{font-size:12px;padding:4px 8px;text-align:right;color:#557277}</style></head>
<body><main id="root"><svg viewBox="0 0 640 440" role="img" aria-label="Kafu MotionCards animation"><g id="art"></g></svg><div id="time"></div></main>
<script>const CONFIG="""+cfgtext+""";const root=document.getElementById('root'),art=document.getElementById('art'),time=document.getElementById('time');"""+custom+"\n"+RUNTIME_JS+"""</script></body></html>"""


def preview_host_html(scene:dict,answer_statements:list[str],port:int)->str:
    qid=str(scene["qid"]);duration=int(scene["duration_ms"]);validate_scene(scene,qid,duration)
    if not isinstance(port,int) or not 1<=port<=65535:raise ValueError("preview_port_invalid")
    child=f"/{qid}.html"
    payload=json.dumps({"qid":qid,"duration_ms":duration,"takeaway":scene["takeaway"],"answers":[str(x) for x in answer_statements],"child":child},ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
    return """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kafu MotionCards preview</title><style>
:root{font-family:system-ui,sans-serif;color:#18363a;background:#eef6f5}body{margin:0}.host{min-height:100dvh;display:grid;grid-template-rows:auto minmax(0,1fr) auto auto;gap:10px;padding:10px;box-sizing:border-box}.bar,.controls{display:flex;gap:8px;align-items:center}.stage{min-height:0;border:2px solid #b9cfcc;border-radius:16px;overflow:hidden;background:white}.stage iframe{width:100%;height:100%;border:0}.final{background:white;border-radius:14px;padding:12px}.controls button{min-width:44px;min-height:44px}.controls input{min-height:44px;flex:1}@media(max-width:430px){.host{padding:6px}}
</style></head><body><main class="host"><header class="bar"><strong>Kafu MotionCards preview</strong><span id="qid"></span></header><section class="stage"><iframe sandbox="allow-scripts" title="MotionCards preview animation"></iframe></section><section class="final" hidden><strong>Takeaway</strong><p class="takeaway"></p><strong>Correct answer</strong><div class="answer"></div></section><footer class="controls"><button id="play" disabled>Play</button><button id="restart" disabled>Restart</button><input id="seek" type="range" min="0" step="50" disabled><output id="time"></output></footer></main>
<script>
const P="""+payload+""",channel=Array.from(crypto.getRandomValues(new Uint8Array(18)),x=>x.toString(16).padStart(2,'0')).join('');
const frame=document.querySelector('iframe'),play=document.getElementById('play'),restart=document.getElementById('restart'),seek=document.getElementById('seek'),time=document.getElementById('time'),final=document.querySelector('.final');
document.getElementById('qid').textContent=P.qid;document.querySelector('.takeaway').textContent=P.takeaway;for(const s of P.answers){const p=document.createElement('p');p.textContent=s;document.querySelector('.answer').appendChild(p)}
seek.max=P.duration_ms;let port=null,playing=false,t=0,anchor=0,raf=0;
const msg=(type,extra={})=>port&&port.postMessage({type,protocol:1,channel_id:channel,qid:P.qid,...extra});
function paint(type='seek'){t=Math.max(0,Math.min(P.duration_ms,t));seek.value=t;time.textContent=(t/1000).toFixed(1)+' / '+(P.duration_ms/1000).toFixed(1)+' s';final.hidden=t<P.duration_ms;msg(type,{time_ms:t})}
function tick(now){if(!playing)return;t=Math.min(P.duration_ms,now-anchor);paint('tick');if(t>=P.duration_ms){playing=false;play.textContent='Replay';return}raf=requestAnimationFrame(tick)}
play.onclick=()=>{if(!port)return;if(playing){playing=false;cancelAnimationFrame(raf);paint('pause');play.textContent='Play';return}if(t>=P.duration_ms){t=0;final.hidden=true;msg('restart',{time_ms:0})}playing=true;anchor=performance.now()-t;msg('play',{time_ms:t});play.textContent='Pause';raf=requestAnimationFrame(tick)};
restart.onclick=()=>{playing=false;cancelAnimationFrame(raf);t=0;play.textContent='Play';msg('restart',{time_ms:0});paint('seek')};seek.oninput=()=>{t=Number(seek.value)||0;if(playing)anchor=performance.now()-t;paint('seek')};
addEventListener('message',ev=>{const m=ev.data;if(ev.source!==frame.contentWindow||!m||m.type!=='kafu-motioncards-ready'||m.channel_id!==channel||m.qid!==P.qid)return;const ch=new MessageChannel();port=ch.port1;port.onmessage=e=>{const x=e.data;if(!x||x.channel_id!==channel||x.qid!==P.qid)return;if(x.type==='ready'){play.disabled=false;restart.disabled=false;seek.disabled=false;paint('seek')}};port.start();frame.contentWindow.postMessage({type:'connect',protocol:1,channel_id:channel,qid:P.qid},'*',[ch.port2])});
frame.src=P.child+'#'+channel;
</script></body></html>"""
