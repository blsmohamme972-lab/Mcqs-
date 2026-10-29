"""Import third-party SVG illustrations into a v2 scene without the model ever reading them.

An author (or AI agent) runs one command; the tool cleans the file, fits it into a box on the
stage, makes its ids unique, records the licence credit, and appends it to ``scene["svg"]``.
The model then only references the illustration by id (``#heart``), so a 60 KB drawing costs
a few tokens instead of ~20k, and two imported files can never break each other's gradients.
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET

SVG="http://www.w3.org/2000/svg"
XLINK="http://www.w3.org/1999/xlink"
EDITOR_NS=("inkscape","sodipodi","sketch","illustrator","adobe","serif","figma","bx")
DROP_TAGS={"metadata","title","desc","script","namedview","foreignObject"}
REF_RE=re.compile(r"url\(\s*(['\"]?)#([^)'\"]+)\1\s*\)")
NUM_RE=re.compile(r"-?(?:\d+\.\d+|\d+\.|\.\d+|\d+)(?:[eE][-+]?\d+)?")

class AssetImportError(ValueError):
    pass

def _local(tag:str)->str:return tag.split("}")[-1]

def _is_editor(name:str)->bool:
    if name.startswith("{"):
        ns=name[1:].split("}")[0].lower()
        return any(x in ns for x in EDITOR_NS)
    return any(name.startswith(x+":") for x in EDITOR_NS)

def _round_numbers(text:str,decimals:int)->str:
    out=[];pos=0
    for m in NUM_RE.finditer(text):
        out.append(text[pos:m.start()]);pos=m.end()
        v=round(float(m.group(0)),decimals)
        s=(f"{v:.{decimals}f}").rstrip("0").rstrip(".") if decimals>0 else str(int(v))
        if s in {"-0","","-"}:s="0"
        prev="".join(out)[-1:] if out else ""
        # Compact SVG syntax lets numbers touch ("1.5.5", "2-3"); never let a rounded number merge with the previous one.
        if prev and (prev.isdigit() or prev==".") and not s.startswith("-"):s=" "+s
        out.append(s)
    out.append(text[pos:])
    return "".join(out)

COLOUR_ATTRS={"fill","stroke","stop-color","flood-color","lighting-color","color","style"}
HEX6_RE=re.compile(r"(?<![(\w])#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3(?![0-9a-fA-F])")
PATH_TOKEN=re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
PATH_ARGS={"M":2,"L":2,"H":1,"V":1,"C":6,"S":4,"Q":4,"T":2,"A":7,"Z":0}

def _fmt(v:float,decimals:int)->str:
    s=f"{round(v,decimals):.{decimals}f}"
    if "." in s:s=s.rstrip("0").rstrip(".")
    if s in ("-0",""):s="0"
    if s.startswith("0."):s=s[1:]
    elif s.startswith("-0."):s="-"+s[2:]
    return s

def _join(nums:list[str])->str:
    """Join numbers with the fewest separators that still parse back unambiguously."""
    out="";last=""
    for n in nums:
        if out and not (n[0]=="-" or (n[0]=="." and "." in last)):out+=" "
        out+=n;last=n
    return out

def optimize_path(d:str,decimals:int)->str:
    """Rewrite path data at a fixed precision without accumulated rounding drift.

    Every point is converted to absolute coordinates and rounded there; each segment is then
    written either absolute or relative to the *rounded* current point, whichever is shorter.
    Relative values are differences of rounded numbers, so errors never add up along a path.
    """
    toks=PATH_TOKEN.findall(d)
    if not toks or toks[0] not in "Mm":return _round_numbers(d,decimals)
    q=10**decimals;R=lambda v:round(v*q)/q
    out=[];cx=cy=sx=sy=0.0;rx=ry=rsx=rsy=0.0;prev="";i=0;cmd=""
    def emit(letter,abs_nums,rel_nums):
        nonlocal prev
        a=[_fmt(v,decimals) for v in abs_nums];r=[_fmt(v,decimals) for v in rel_nums]
        A=letter.upper(),_join(a);Rl=letter.lower(),_join(r)
        best=min((A,Rl),key=lambda x:len(x[1])+(0 if x[0]==prev else 1))
        if best[0]==prev and prev not in "Mm":
            tail=re.findall(r"-?[\d.]+$",out[-1]);lastnum=tail[0] if tail else ""
            out.append(("" if best[1][0]=="-" or (best[1][0]=="." and "." in lastnum) else " ")+best[1])
        else:out.append(best[0]+best[1])
        prev=best[0]
    while i<len(toks):
        t=toks[i]
        if t.isalpha():cmd=t;i+=1
        elif not cmd:raise AssetImportError("path data starts with a number")
        U=cmd.upper();rel=cmd.islower();n=PATH_ARGS[U]
        if U=="Z":
            out.append("z");prev="z";cx,cy,rx,ry=sx,sy,rsx,rsy;cmd="";continue
        if i+n>len(toks):raise AssetImportError("truncated path data")
        args=[float(x) for x in toks[i:i+n]];i+=n
        if U=="A":
            ex,ey=(cx+args[5],cy+args[6]) if rel else (args[5],args[6])
            Ex,Ey=R(ex),R(ey);fl=[args[0],args[1],args[2],1.0 if args[3] else 0.0,1.0 if args[4] else 0.0]
            a=[_fmt(v,decimals) for v in fl[:3]]+[str(int(fl[3])),str(int(fl[4]))]
            ab=" ".join(a+[_fmt(Ex,decimals),_fmt(Ey,decimals)]);rl=" ".join(a+[_fmt(Ex-rx,decimals),_fmt(Ey-ry,decimals)])
            best=("A",ab) if len(ab)<=len(rl) else ("a",rl);out.append(best[0]+best[1]);prev=best[0]
            cx,cy,rx,ry=ex,ey,Ex,Ey
        elif U=="H":
            ex=cx+args[0] if rel else args[0];Ex=R(ex);emit("H",[Ex],[Ex-rx]);cx,rx=ex,Ex
        elif U=="V":
            ey=cy+args[0] if rel else args[0];Ey=R(ey);emit("V",[Ey],[Ey-ry]);cy,ry=ey,Ey
        else:
            pts=[(cx+args[k],cy+args[k+1]) if rel else (args[k],args[k+1]) for k in range(0,n,2)]
            P=[(R(x),R(y)) for x,y in pts]
            emit(U,[v for p in P for v in p],[v for x,y in P for v in (x-rx,y-ry)])
            cx,cy=pts[-1];rx,ry=P[-1]
            if U=="M":sx,sy,rsx,rsy=cx,cy,rx,ry;cmd="l" if rel else "L"
    return "".join(out)

def auto_decimals(scale:float,tolerance:float=0.1)->int:
    """Fewest decimals whose worst-case rounding error stays under `tolerance` stage pixels."""
    for d in range(0,4):
        if 0.5*10**-d*scale<=tolerance:return d
    return 4

def _viewbox(root)->tuple[float,float,float,float]:
    vb=root.get("viewBox")
    if vb:
        parts=[float(x) for x in re.split(r"[\s,]+",vb.strip()) if x]
        if len(parts)==4 and parts[2]>0 and parts[3]>0:return tuple(parts)
    def size(v):
        m=re.match(r"\s*([0-9.]+)",str(v or ""))
        return float(m.group(1)) if m else 0.0
    w,h=size(root.get("width")),size(root.get("height"))
    if w>0 and h>0:return (0.0,0.0,w,h)
    raise AssetImportError("the SVG has no usable viewBox or width/height")

def prepare_svg(source:str,asset_id:str,box:tuple[float,float,float,float],decimals:int|None=None,fit:str="contain")->str:
    """Return a cleaned ``<g id=asset_id ...>`` fragment scaled into box=(x,y,w,h) stage pixels."""
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}",asset_id):raise AssetImportError("id must match ^[a-z][a-z0-9_-]{0,31}$")
    # Illustrator exports declare its namespace URIs as entities (<!ENTITY ns_ai "http://ns.adobe.com/...">)
    # and use them only as whole attribute values (xmlns:i="&ns_ai;", requiredExtensions="&ns_ai;"). Accept exactly
    # that: plain URL literals used as a complete attribute value. Any other entity (external, parameter, markup,
    # or referenced in text) is still refused.
    doctype=re.search(r"<!DOCTYPE[^>\[]*(\[([^\]]*)\])?\s*>",source,flags=re.I|re.S)
    ns_entities={}
    if doctype and doctype.group(2):
        subset=re.sub(r"<!--.*?-->","",doctype.group(2),flags=re.S)
        decls=re.findall(r"<!ENTITY[^>]*>",subset,flags=re.I)
        for d in decls:
            m=re.fullmatch(r'<!ENTITY\s+([A-Za-z_][\w.-]*)\s+"(https?://[^"\s<>&%]+)"\s*>',d.strip())
            if not m:raise AssetImportError("SVG declares entities; refusing to import")
            ns_entities[m.group(1)]=m.group(2)
        if re.sub(r"<!ENTITY[^>]*>","",subset,flags=re.I).strip():raise AssetImportError("SVG doctype has unsupported declarations")
    text=re.sub(r"<!DOCTYPE[^>\[]*(\[[^\]]*\])?\s*>","",source,flags=re.I|re.S)
    text=re.sub(r"<\?xml[^>]*\?>","",text)
    if re.search(r"<!ENTITY",text,re.I):raise AssetImportError("SVG declares entities; refusing to import")
    if ns_entities:
        text=re.sub(r'(\s[\w:.-]+=")&([A-Za-z_][\w.-]*);(")',lambda m:m.group(1)+ns_entities[m.group(2)]+m.group(3) if m.group(2) in ns_entities else m.group(0),text)
    try:root=ET.fromstring(text)
    except ET.ParseError as exc:raise AssetImportError(f"not well-formed SVG: {exc}") from None
    if _local(root.tag)!="svg":raise AssetImportError("root element is not <svg>")
    vx,vy,vw,vh=_viewbox(root)
    x,y,w,h=box
    sx,sy=w/vw,h/vh
    if fit=="contain":s=min(sx,sy);sx=sy=s
    elif fit=="cover":s=max(sx,sy);sx=sy=s
    elif fit!="stretch":raise AssetImportError("fit must be contain, cover or stretch")
    if decimals is None:
        decimals=auto_decimals(max(sx,sy))
        # Inner scale/matrix transforms change the effective scale; keep one extra decimal for them.
        if any(re.search(r"scale|matrix",el.get("transform","")) for el in root.iter()):decimals+=1
    # Collect ids first so every internal reference can be rewritten consistently.
    ids={el.get("id") for el in root.iter() if el.get("id")}
    rename={old:f"{asset_id}-{i}" for i,old in enumerate(sorted(ids))}
    def fix_refs(value:str)->str:
        value=REF_RE.sub(lambda m:f"url(#{rename.get(m.group(2),m.group(2))})",value)
        return value
    def clean(el):
        for child in list(el):
            tag=_local(child.tag) if isinstance(child.tag,str) else ""
            if not isinstance(child.tag,str) or tag in DROP_TAGS or _is_editor(child.tag):
                el.remove(child);continue
            clean(child)
        for name in list(el.attrib):
            if _is_editor(name):del el.attrib[name];continue
            val=el.attrib[name];lname=_local(name)
            if lname.startswith("on"):del el.attrib[name];continue
            if lname=="id":el.attrib[name]=rename.get(val,val);continue
            if lname=="href":
                if val.startswith("#"):el.attrib[name]="#"+rename.get(val[1:],val[1:])
                elif val.startswith("data:image/"):pass
                else:raise AssetImportError(f"<{_local(el.tag)}> links to an external file ({val[:60]}); embed it first")
                if name!="href":del el.attrib[name];el.set("href",val if not val.startswith("#") else "#"+rename.get(val[1:],val[1:]))
                continue
            if re.search(r"url\(\s*['\"]?\s*(?:https?:)?//",val,re.I):raise AssetImportError("SVG references an external url()")
            val=fix_refs(val)
            if lname in COLOUR_ATTRS:val=HEX6_RE.sub(r"#\1\2\3",val)
            if lname=="d":val=optimize_path(val,decimals)
            elif lname in {"points","transform","x","y","x1","y1","x2","y2","cx","cy","r","rx","ry","width","height","stroke-width","offset","fx","fy","gradientTransform","stdDeviation"}:
                val=_round_numbers(val,max(decimals,2))   # offsets, widths and radii keep 2 decimals
            el.attrib[name]=val
        if _local(el.tag)=="style" and el.text:
            if re.search(r"@import|url\(\s*['\"]?\s*(?:https?:)?//",el.text,re.I):raise AssetImportError("<style> imports external CSS")
            css=fix_refs(el.text)
            # Scope class selectors so two imported files cannot restyle each other.
            css=re.sub(r"\.([A-Za-z_][\w-]*)",lambda m:f".{asset_id}-{m.group(1)}",css)
            css=re.sub(r"#([A-Za-z_][\w-]*)(?=[\s,{.:>+~\[])",lambda m:"#"+rename.get(m.group(1),m.group(1)),css)
            el.text=css
        cls=el.get("class")
        if cls:el.set("class"," ".join(f"{asset_id}-{c}" for c in cls.split()))
    clean(root)
    tx=x+(w-vw*sx)/2-vx*sx;ty=y+(h-vh*sy)/2-vy*sy
    ET.register_namespace("",SVG);ET.register_namespace("xlink",XLINK)
    inner="".join(ET.tostring(child,encoding="unicode") for child in root)
    inner=inner.replace(f' xmlns="{SVG}"',"").replace(f" xmlns:ns0=\"{SVG}\"","").replace("ns0:","")
    inner=re.sub(r"\s+xmlns:xlink=\"[^\"]+\"","",inner)
    inner=re.sub(r">\s+<","><",inner)
    t=lambda v:("%.3f"%v).rstrip("0").rstrip(".")
    return f'<g id="{asset_id}" transform="translate({t(tx)} {t(ty)}) scale({t(sx)} {t(sy)})">{inner}</g>'

def prepare_template(source:str,asset_id:str,width:float,height:float,decimals:int|None=None)->str:
    """A reusable symbol centred on (0,0), placed in <defs>: draw copies with <use href="#id" x= y=>."""
    return "<defs>"+prepare_svg(source,asset_id,(-width/2,-height/2,width,height),decimals,"contain")+"</defs>"

RESTRICTED_LICENCE=re.compile(r"\b(?:CC[\s-]*)?BY[\s-]*(?:NC|ND)\b|\bnon[\s-]?commercial\b|\bno[\s-]?derivatives?\b",re.I)

def check_credit(credit:str|None):
    """Cards are modified derivatives and the app may be paid: NC/ND material is never allowed."""
    if credit and RESTRICTED_LICENCE.search(credit):
        raise AssetImportError("NC (non-commercial) or ND (no-derivatives) licences are not allowed in MotionCards; choose public-domain, CC0 or CC BY/BY-SA art")

def add_to_scene(scene:dict,fragment:str,credit:str|None=None)->dict:
    """Append an imported fragment to scene['svg'] (creating it) and record the credit."""
    check_credit(credit)
    svg=scene.get("svg") or '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    if "</svg>" not in svg:raise AssetImportError("scene svg has no closing </svg>")
    m=re.search(r'<g id="([a-z][a-z0-9_-]*)"',fragment)
    if m and re.search(r'\bid="'+re.escape(m.group(1))+r'"',svg):raise AssetImportError(f"id {m.group(1)!r} already exists in scene.svg")
    head,tail=svg.rsplit("</svg>",1)
    scene["svg"]=head+fragment+"</svg>"+tail
    if credit:
        credits=list(scene.get("credits") or [])
        if credit not in credits:credits.append(credit)
        scene["credits"]=credits
    return scene

LIBRARY_DIR=__import__("pathlib").Path(__file__).resolve().parent.parent/"library"

def library_index()->dict:
    import json
    return json.loads((LIBRARY_DIR/"library.json").read_text(encoding="utf-8"))

def library_art(name:str)->tuple[str,str]:
    """Return (svg text, credit) for a bundled illustration (``lib:<name>``)."""
    idx=library_index();item=idx["art"].get(name)
    if not item:raise AssetImportError(f"no library art {name!r}; run: motioncards.py library")
    return (LIBRARY_DIR/item["file"]).read_text(encoding="utf-8"),item.get("credit") or idx["credit"]

def add_style_kit(scene:dict)->bool:
    """Put the shared shading kit (<defs id="kit">: kit-volume, kit-tissue, ...) into scene['svg'] once.

    Returns False when the scene already has it. The kit is plain SVG inside the scene, so it is
    validated and compiled like any other markup and needs nothing new in the runtime.
    """
    svg=scene.get("svg") or '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    if 'id="kit"' in svg:return False
    if "</svg>" not in svg:raise AssetImportError("scene svg has no closing </svg>")
    kit=(LIBRARY_DIR/"style_kit.svg").read_text(encoding="utf-8")
    defs=re.search(r"<defs id=\"kit\">.*</defs>",kit,re.S).group(0)
    defs=re.sub(r">\s+<","><",defs)
    m=re.match(r"(<svg[^>]*>)",svg)
    scene["svg"]=svg[:m.end()]+defs+svg[m.end():] if m else svg
    return True

RECIPES_BEGIN="// @recipes v1 begin"

def add_recipes(scene:dict)->bool:
    """Prepend the tested animation recipes (const R = {...}) to scene['script'] once.

    Plain author code inside the scene: validated and compiled like any script, no runtime change.
    """
    script=str(scene.get("script") or "")
    if RECIPES_BEGIN in script:return False
    scene["script"]=(LIBRARY_DIR/"recipes.js").read_text(encoding="utf-8").rstrip("\n")+"\n"+script
    return True
