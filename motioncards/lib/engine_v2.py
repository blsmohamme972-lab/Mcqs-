"""Kafu MotionCards scene engine v2.

Schema v1 scenes are compiled by ``compiler.py`` exactly as before (byte-identical), so
already-built v1 packages keep validating.  Scenes declaring ``"schema_version": 2`` are
validated and compiled here.  The host/iframe protocol, the public index runtime_version and
the HTTP CSP are unchanged: v2 only changes what the self-contained entry draws.

Every check below exists so that an authoring mistake fails *here*, with a precise
``scene_v2_invalid:<path>:<reason>`` message, instead of failing in the publisher or on a
student's phone.
"""
from __future__ import annotations
import base64,binascii,json,math,re
import xml.etree.ElementTree as ET

SCENE_V2_KEYS={"schema_version","qid","duration_ms","takeaway","replace","stage","palette","gradients","assets","camera","layers","svg","script","custom_renderer","credits"}
MAX_SCENE_BYTES=1_500_000
MAX_NODES=400
MAX_DEPTH=6
MAX_KEYS=80
MAX_PARTICLES_TOTAL=1000
MAX_ASSETS=12
MAX_ASSET_BYTES=600*1024
MAX_ASSET_CHARS_TOTAL=1_200_000
MAX_PATH_CHARS=8000
MAX_TEXT_CHARS=300
MAX_CUSTOM_CHARS=20000
MAX_SVG_CHARS=1_200_000
MAX_SCRIPT_CHARS=800_000
SVG_NS="{http://www.w3.org/2000/svg}"
ABS_LIMIT=100000

EASINGS={"linear","ease_in","ease_out","ease_in_out","sine","back_out","back_in","elastic_out","bounce_out","step"}
ENTER_EFFECTS={"none","fade","pop","grow","draw","type","slide_up","slide_down","slide_left","slide_right"}
EXIT_EFFECTS={"none","fade","shrink","slide_up","slide_down","slide_left","slide_right"}
FONTS={"sans","serif","mono","rounded"}

# Built-in colour tokens, used as "@name".  Mirrored in the JS runtime below.
BUILTIN_TOKENS={
 "ink":"#16323a","muted":"#5f7a80","paper":"#fbfaf7","surface":"#e9f2f2","line":"#c9dadb",
 "accent":"#e76f51","good":"#2a9d8f","bad":"#d62828","warn":"#f4a261","highlight":"#ffd166","info":"#3a86ff",
 "artery":"#d64545","artery_dark":"#9e2a2b","vein":"#3b6fb6","vein_dark":"#274b80","blood":"#b3202a","plasma":"#f6d58e",
 "nerve":"#f2c14e","myelin":"#f7e7b4","muscle":"#c8553d","tendon":"#e8dcc4","bone":"#efe6d2","cartilage":"#cfe3e8",
 "fat":"#f4d35e","skin":"#f1c7a8","mucosa":"#e89aa6","lymph":"#9bc995","bacteria":"#6a994e","virus":"#8e5ba6",
 "drug":"#2a9d8f","enzyme":"#e76f51","membrane":"#e9c46a","water":"#4cc9f0","oxygen":"#e63946","co2":"#6c757d",
 "cell":"#fde2e4","nucleus":"#7b6d8d","bile":"#9a8f2f","air":"#d8f3ff"
}
CSS_NAMED={
 "aliceblue","antiquewhite","aqua","aquamarine","azure","beige","bisque","black","blanchedalmond","blue","blueviolet","brown","burlywood",
 "cadetblue","chartreuse","chocolate","coral","cornflowerblue","cornsilk","crimson","cyan","darkblue","darkcyan","darkgoldenrod","darkgray",
 "darkgreen","darkgrey","darkkhaki","darkmagenta","darkolivegreen","darkorange","darkorchid","darkred","darksalmon","darkseagreen",
 "darkslateblue","darkslategray","darkslategrey","darkturquoise","darkviolet","deeppink","deepskyblue","dimgray","dimgrey","dodgerblue",
 "firebrick","floralwhite","forestgreen","fuchsia","gainsboro","ghostwhite","gold","goldenrod","gray","green","greenyellow","grey",
 "honeydew","hotpink","indianred","indigo","ivory","khaki","lavender","lavenderblush","lawngreen","lemonchiffon","lightblue","lightcoral",
 "lightcyan","lightgoldenrodyellow","lightgray","lightgreen","lightgrey","lightpink","lightsalmon","lightseagreen","lightskyblue",
 "lightslategray","lightslategrey","lightsteelblue","lightyellow","lime","limegreen","linen","magenta","maroon","mediumaquamarine",
 "mediumblue","mediumorchid","mediumpurple","mediumseagreen","mediumslateblue","mediumspringgreen","mediumturquoise","mediumvioletred",
 "midnightblue","mintcream","mistyrose","moccasin","navajowhite","navy","oldlace","olive","olivedrab","orange","orangered","orchid",
 "palegoldenrod","palegreen","paleturquoise","palevioletred","papayawhip","peachpuff","peru","pink","plum","powderblue","purple",
 "rebeccapurple","red","rosybrown","royalblue","saddlebrown","salmon","sandybrown","seagreen","seashell","sienna","silver","skyblue",
 "slateblue","slategray","slategrey","snow","springgreen","steelblue","tan","teal","thistle","tomato","turquoise","violet","wheat",
 "white","whitesmoke","yellow","yellowgreen","none","transparent"
}
HEX_RE=re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
NUM=r"\s*-?(?:\d+\.?\d*|\.\d+)\s*"
RGB_RE=re.compile(r"^rgba?\("+NUM+","+NUM+","+NUM+"(?:,"+NUM+r")?\)$")
HSL_RE=re.compile(r"^hsla?\("+NUM+","+NUM+"%,"+NUM+"%(?:,"+NUM+r")?\)$")
ID_RE=re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
TOKEN_NAME_RE=re.compile(r"^[a-z][a-z0-9_]{0,23}$")
PATH_RE=re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9eE.,+\-\s]*$")
PATH_NUM_RE=re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
# Author code runs inside the sandboxed, network-less iframe (sandbox="allow-scripts", strict CSP);
# that is the security boundary.  Only sequences that would break the HTML document are rejected.
SCRIPT_BREAKERS=re.compile(r"</script|<script|<!--",re.I)
EXTERNAL_REF=re.compile(r"^\s*(?:https?:)?//",re.I)

TRANSFORM_KEYS={"x","y","scale","scale_x","scale_y","rotate","opacity"}
PAINT_KEYS={"fill","stroke","stroke_width"}
SHAPE_FIELDS={
 "rect":{"x","y","width","height","rx"},"highlight":{"x","y","width","height","rx"},"focus":{"x","y","width","height","rx"},
 "circle":{"cx","cy","r"},"ellipse":{"cx","cy","rx","ry"},
 "line":{"x1","y1","x2","y2"},"arrow":{"x1","y1","x2","y2","bend","head","head_size"},
 "path":{"d"},"polygon":{"points"},"polyline":{"points"},
 "text":{"text","x","y","size","weight","color","anchor","font","italic","max_width","line_height","fit","max_lines","box","halo","letter_spacing"},
 "image":{"asset","x","y","width","height","fit"},
 "group":{"x","y","layers"},
 "particles":{"d","count","r","shape","speed","spread","seed","size_jitter","phase","guide","fade_ends"},
 "spotlight":{"cx","cy","r","x","y","width","height","rx","dim","color"},
}
SHAPE_FIELDS["label"]=SHAPE_FIELDS["text"]
REQUIRED={"rect":{"width","height"},"highlight":{"width","height"},"focus":{"width","height"},"circle":{"r"},"ellipse":{"rx","ry"},
 "line":{"x1","y1","x2","y2"},"arrow":{"x1","y1","x2","y2"},"path":{"d"},"polygon":{"points"},"polyline":{"points"},
 "text":{"text"},"label":{"text"},"image":{"asset","width","height"},"group":{"layers"},"particles":{"d"},"spotlight":set()}
COMMON_FIELDS={"type","id","fixed","show","enter","exit","keys","repeat","origin","along","opacity","fill","stroke","stroke_width",
 "fill_opacity","stroke_opacity","dash","linecap","linejoin","shadow","glow","blur"}
GEOMETRY_KEYS={
 "rect":{"width","height","rx"},"highlight":{"width","height","rx"},"focus":{"width","height","rx"},
 "circle":{"cx","cy","r"},"ellipse":{"cx","cy","rx","ry"},"line":{"x1","y1","x2","y2"},"arrow":{"x1","y1","x2","y2","bend"},
 "path":{"d"},"polygon":set(),"polyline":set(),"text":set(),"label":set(),"image":set(),"group":set(),
 "particles":{"speed"},"spotlight":{"cx","cy","r","x","y","width","height","dim"},
}
DRAWABLE={"rect","highlight","focus","circle","ellipse","line","arrow","path","polygon","polyline"}
NON_NEGATIVE={"width","height","r","rx","ry","stroke_width","size","max_width","head_size","count","spread","blur","scale","scale_x","scale_y"}
V1_ONLY={"start_ms","end_ms","from","to"}

class SceneV2Error(ValueError):
    pass

def _fail(path:str,msg:str):
    raise SceneV2Error(f"scene_v2_invalid:{path}:{msg}")

def _num(v,path,lo=-ABS_LIMIT,hi=ABS_LIMIT):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):_fail(path,"must be a finite number")
    if v<lo or v>hi:_fail(path,f"must be between {lo} and {hi}")
    return v

def _int(v,path,lo,hi):
    if isinstance(v,bool) or not isinstance(v,int):_fail(path,"must be an integer")
    if v<lo or v>hi:_fail(path,f"must be between {lo} and {hi}")
    return v

def _str(v,path,maxlen):
    if not isinstance(v,str):_fail(path,"must be a string")
    if len(v)>maxlen:_fail(path,f"longer than {maxlen} characters")
    return v

def _bool(v,path):
    if not isinstance(v,bool):_fail(path,"must be true or false")
    return v

class _Ctx:
    def __init__(self,scene:dict,duration:int):
        self.duration=duration
        self.tokens=dict(BUILTIN_TOKENS)
        self.gradients=set();self.assets=set();self.used_assets=set()
        self.nodes=0;self.particles=0

def _color(v,path,ctx:_Ctx,interpolable=False):
    if not isinstance(v,str) or not v or len(v)>64:_fail(path,"colour must be a short string")
    if v.startswith("@"):
        if v[1:] not in ctx.tokens:_fail(path,f"unknown colour token {v}; built-ins: "+", ".join("@"+k for k in sorted(BUILTIN_TOKENS)))
        return v
    if v.startswith("url:"):
        if interpolable:_fail(path,"gradients cannot be animated in keys; animate opacity or use solid colours")
        if v[4:] not in ctx.gradients:_fail(path,f"unknown gradient {v[4:]}")
        return v
    if HEX_RE.fullmatch(v) or RGB_RE.fullmatch(v) or HSL_RE.fullmatch(v):return v
    if v.lower() in CSS_NAMED:
        if interpolable and v.lower() not in {"none","transparent"}:_fail(path,"animated colours must be #hex, rgb(), hsl() or @token")
        if interpolable:_fail(path,"none/transparent cannot be animated; animate opacity instead")
        return v
    _fail(path,"invalid colour (use #hex, rgb(), hsl(), a CSS colour name, @token or url:gradient-id)")

def _path_d(v,path):
    d=_str(v,path,MAX_PATH_CHARS)
    if not d.strip():_fail(path,"path is empty")
    if not PATH_RE.fullmatch(d):_fail(path,"path may only contain SVG path commands and numbers")
    if d.strip()[0] not in "Mm":_fail(path,"path must start with M or m")
    for n in PATH_NUM_RE.findall(d):
        if not math.isfinite(float(n)) or abs(float(n))>ABS_LIMIT:_fail(path,"path number out of range")
    return d

def _path_skeleton(d:str):
    return (PATH_NUM_RE.sub("#",d).replace(" ","").replace(",","").replace("\n","").replace("\t","").replace("\r",""),len(PATH_NUM_RE.findall(d)))

def _points(v,path):
    if not isinstance(v,list) or not 2<=len(v)<=200:_fail(path,"points must be a list of 2..200 [x,y] pairs")
    for i,p in enumerate(v):
        if not isinstance(p,list) or len(p)!=2:_fail(f"{path}[{i}]","each point must be [x,y]")
        _num(p[0],f"{path}[{i}][0]");_num(p[1],f"{path}[{i}][1]")

def _ease(v,path):
    if v not in EASINGS:_fail(path,"unknown easing; use one of "+", ".join(sorted(EASINGS)))

def _effect(v,path,allowed,window_ms):
    if isinstance(v,str):
        if v not in allowed:_fail(path,"unknown effect; use one of "+", ".join(sorted(allowed)))
        return
    if not isinstance(v,dict):_fail(path,"must be an effect name or {effect,ms,ease}")
    extra=set(v)-{"effect","ms","ease"}
    if extra:_fail(path,"unknown fields "+", ".join(sorted(extra)))
    if v.get("effect") not in allowed:_fail(path+".effect","unknown effect; use one of "+", ".join(sorted(allowed)))
    if "ms" in v:_int(v["ms"],path+".ms",50,30000)
    if "ease" in v:_ease(v["ease"],path+".ease")

def _validate_keys(keys,path,ltype,ctx:_Ctx,limit:int,base:dict,has_along:bool):
    if not isinstance(keys,list) or not 1<=len(keys)<=MAX_KEYS:_fail(path,f"keys must be a list of 1..{MAX_KEYS} keyframes")
    allowed=TRANSFORM_KEYS|GEOMETRY_KEYS[ltype]|{"t","ease"}
    if ltype in DRAWABLE:allowed|={"draw"}|PAINT_KEYS
    elif ltype in {"text","label"}:allowed|={"fill"}
    elif ltype=="particles":allowed|={"fill","stroke"}
    elif ltype=="spotlight":allowed|={"fill"}
    if has_along:allowed|={"progress"}
    last=-1
    for i,k in enumerate(keys):
        kp=f"{path}[{i}]"
        if not isinstance(k,dict):_fail(kp,"keyframe must be an object")
        extra=set(k)-allowed
        if extra:_fail(kp,"property not animatable for "+ltype+": "+", ".join(sorted(extra))+"; allowed: "+", ".join(sorted(allowed-{"t","ease"})))
        if "t" not in k:_fail(kp,"keyframe needs t (milliseconds)")
        t=_int(k["t"],kp+".t",0,limit)
        if t<last:_fail(kp+".t","keyframes must be in time order")
        last=t
        if len(set(k)-{"t","ease"})==0:_fail(kp,"keyframe animates nothing")
        if "ease" in k:_ease(k["ease"],kp+".ease")
        for prop,val in k.items():
            if prop in {"t","ease"}:continue
            pp=f"{kp}.{prop}"
            if prop in {"fill","stroke"}:_color(val,pp,ctx,interpolable=True)
            elif prop=="d":
                _path_d(val,pp)
                if re.search(r"[Aa]",val) or re.search(r"[Aa]",str(base.get("d",""))):_fail(pp,"path morphing does not support arc (A) commands; use C or Q curves")
                if _path_skeleton(val)!=_path_skeleton(str(base.get("d",""))):_fail(pp,"morph target must have exactly the same commands and number count as the layer's d")
            elif prop in {"opacity","draw","progress","dim"}:_num(val,pp,0,1)
            elif prop in NON_NEGATIVE:_num(val,pp,0)
            elif prop=="rotate":_num(val,pp,-36000,36000)
            else:_num(val,pp)

def _validate_text(layer,path,ctx):
    text=_str(layer["text"],path+".text",MAX_TEXT_CHARS)
    if not text.strip():_fail(path+".text","text is empty")
    if text.strip().upper().startswith("EDIT:"):_fail(path+".text","unfinished EDIT: placeholder text")
    if "size" in layer:_num(layer["size"],path+".size",6,200)
    if "weight" in layer:
        w=layer["weight"]
        if not ((isinstance(w,int) and not isinstance(w,bool) and 100<=w<=900 and w%100==0) or w in {"normal","bold"}):_fail(path+".weight","use 100..900 (multiple of 100), normal or bold")
    if "color" in layer:_color(layer["color"],path+".color",ctx)
    if "color" in layer and "fill" in layer:_fail(path,"use either color or fill for text, not both")
    if "anchor" in layer and layer["anchor"] not in {"start","middle","end"}:_fail(path+".anchor","use start, middle or end")
    if "font" in layer and layer["font"] not in FONTS:_fail(path+".font","use one of "+", ".join(sorted(FONTS)))
    if "italic" in layer:_bool(layer["italic"],path+".italic")
    if "max_width" in layer:_num(layer["max_width"],path+".max_width",20,4000)
    if "line_height" in layer:_num(layer["line_height"],path+".line_height",0.8,3)
    if "fit" in layer:_bool(layer["fit"],path+".fit")
    if "max_lines" in layer:_int(layer["max_lines"],path+".max_lines",1,12)
    if ("fit" in layer or "max_lines" in layer) and "max_width" not in layer:_fail(path,"fit/max_lines need max_width")
    if "letter_spacing" in layer:_num(layer["letter_spacing"],path+".letter_spacing",-10,40)
    if "halo" in layer:_color(layer["halo"],path+".halo",ctx)
    if "box" in layer:
        b=layer["box"]
        if not isinstance(b,dict):_fail(path+".box","box must be an object")
        extra=set(b)-{"fill","stroke","stroke_width","pad","rx","opacity"}
        if extra:_fail(path+".box","unknown fields "+", ".join(sorted(extra)))
        for k in ("fill","stroke"):
            if k in b:_color(b[k],f"{path}.box.{k}",ctx)
        for k,lo,hi in (("stroke_width",0,40),("pad",0,200),("rx",0,400),("opacity",0,1)):
            if k in b:_num(b[k],f"{path}.box.{k}",lo,hi)

def _validate_layer(layer,path,ctx:_Ctx,depth:int,ids:set):
    if not isinstance(layer,dict):_fail(path,"layer must be an object")
    ltype=layer.get("type")
    if ltype not in SHAPE_FIELDS:_fail(path+".type","unknown layer type; use one of "+", ".join(sorted(SHAPE_FIELDS)))
    ctx.nodes+=1
    if ctx.nodes>MAX_NODES:_fail(path,f"scene has more than {MAX_NODES} layers in total")
    v1=set(layer)&V1_ONLY
    if v1:_fail(path,"schema v2 uses show/enter/exit/keys instead of "+", ".join(sorted(v1)))
    extra=set(layer)-COMMON_FIELDS-SHAPE_FIELDS[ltype]
    if extra:_fail(path,f"unknown fields for {ltype}: "+", ".join(sorted(extra)))
    missing=REQUIRED[ltype]-set(layer)
    if missing:_fail(path,f"{ltype} needs "+", ".join(sorted(missing)))
    if "fixed" in layer:
        _bool(layer["fixed"],path+".fixed")
        if depth!=1:_fail(path+".fixed","fixed (ignore the camera) is only allowed on top-level layers")
    if "id" in layer:
        if not isinstance(layer["id"],str) or not ID_RE.fullmatch(layer["id"]):_fail(path+".id","id must match ^[a-z][a-z0-9_-]{0,31}$")
        if layer["id"] in ids:_fail(path+".id","duplicate layer id")
        ids.add(layer["id"])
    D=ctx.duration
    start,end=0,D
    if "show" in layer:
        s=layer["show"]
        if not isinstance(s,list) or len(s)!=2:_fail(path+".show","show must be [start_ms,end_ms]")
        start=_int(s[0],path+".show[0]",0,D);end=_int(s[1],path+".show[1]",0,D)
        if end<=start:_fail(path+".show","end must be after start")
    if "enter" in layer:_effect(layer["enter"],path+".enter",ENTER_EFFECTS,end-start)
    if "exit" in layer:_effect(layer["exit"],path+".exit",EXIT_EFFECTS,end-start)
    for eff in ("enter","exit"):
        e=layer.get(eff);name=e if isinstance(e,str) else (e or {}).get("effect")
        if name=="draw" and ltype not in DRAWABLE:_fail(path+"."+eff,"draw only works on stroked shapes (rect, circle, ellipse, line, arrow, path, polygon, polyline)")
        if name=="type" and ltype not in {"text","label"}:_fail(path+"."+eff,"type only works on text")
    for k in ("x","y","cx","cy","x1","y1","x2","y2","bend"):
        if k in layer:_num(layer[k],f"{path}.{k}")
    for k in ("width","height","r","rx","ry"):
        if k in layer:_num(layer[k],f"{path}.{k}",0)
    for k in ("opacity","fill_opacity","stroke_opacity"):
        if k in layer:_num(layer[k],f"{path}.{k}",0,1)
    if "stroke_width" in layer:_num(layer["stroke_width"],path+".stroke_width",0,80)
    for k in ("fill","stroke"):
        if k in layer:_color(layer[k],f"{path}.{k}",ctx)
    if "dash" in layer:
        d=layer["dash"]
        if not isinstance(d,list) or not 1<=len(d)<=8:_fail(path+".dash","dash must be a list of 1..8 numbers")
        for i,x in enumerate(d):_num(x,f"{path}.dash[{i}]",0,1000)
        if not any(d):_fail(path+".dash","dash cannot be all zeros")
    if "linecap" in layer and layer["linecap"] not in {"butt","round","square"}:_fail(path+".linecap","use butt, round or square")
    if "linejoin" in layer and layer["linejoin"] not in {"miter","round","bevel"}:_fail(path+".linejoin","use miter, round or bevel")
    if "shadow" in layer and layer["shadow"] not in {False,True,"soft","strong"}:_fail(path+".shadow","use true, false, soft or strong")
    if "glow" in layer:_color(layer["glow"],path+".glow",ctx)
    if "blur" in layer:_num(layer["blur"],path+".blur",0,40)
    if "origin" in layer:
        o=layer["origin"]
        if o!="center" and not (isinstance(o,list) and len(o)==2):_fail(path+".origin",'origin must be "center" or [x,y]')
        if isinstance(o,list):_num(o[0],path+".origin[0]");_num(o[1],path+".origin[1]")
    has_along="along" in layer
    if has_along:
        a=layer["along"]
        if not isinstance(a,dict) or "d" not in a:_fail(path+".along","along must be {d, rotate?}")
        extra=set(a)-{"d","rotate"}
        if extra:_fail(path+".along","unknown fields "+", ".join(sorted(extra)))
        _path_d(a["d"],path+".along.d")
        if "rotate" in a:_bool(a["rotate"],path+".along.rotate")
    limit=D
    if "repeat" in layer:
        r=layer["repeat"]
        if not isinstance(r,dict) or "every_ms" not in r:_fail(path+".repeat","repeat must be {every_ms, from_ms?, times?}")
        extra=set(r)-{"every_ms","from_ms","times"}
        if extra:_fail(path+".repeat","unknown fields "+", ".join(sorted(extra)))
        limit=_int(r["every_ms"],path+".repeat.every_ms",100,D)
        if "from_ms" in r:_int(r["from_ms"],path+".repeat.from_ms",0,D)
        if "times" in r:_int(r["times"],path+".repeat.times",1,1000)
        if "keys" not in layer:_fail(path+".repeat","repeat needs keys (key t values are inside one cycle: 0..every_ms)")
    if ltype=="path":_path_d(layer["d"],path+".d")
    if "keys" in layer:_validate_keys(layer["keys"],path+".keys",ltype,ctx,limit,layer,has_along)
    # type specific
    if ltype in {"polygon","polyline"}:_points(layer["points"],path+".points")
    if ltype=="arrow":
        if "head" in layer and layer["head"] not in {"end","start","both","none"}:_fail(path+".head","use end, start, both or none")
        if "head_size" in layer:_num(layer["head_size"],path+".head_size",0,200)
    if ltype in {"text","label"}:_validate_text(layer,path,ctx)
    if ltype=="image":
        if layer["asset"] not in ctx.assets:_fail(path+".asset","unknown asset id (declare it in scene.assets)")
        ctx.used_assets.add(layer["asset"])
        if "fit" in layer and layer["fit"] not in {"contain","cover","stretch"}:_fail(path+".fit","use contain, cover or stretch")
    if ltype=="group":
        if depth>=MAX_DEPTH:_fail(path,f"groups may be nested at most {MAX_DEPTH} levels")
        kids=layer["layers"]
        if not isinstance(kids,list) or not 1<=len(kids)<=MAX_NODES:_fail(path+".layers","group needs a non-empty layers list")
        for i,child in enumerate(kids):_validate_layer(child,f"{path}.layers[{i}]",ctx,depth+1,ids)
    if ltype=="particles":
        _path_d(layer["d"],path+".d")
        count=_int(layer.get("count",24),path+".count",1,200)
        ctx.particles+=count
        if ctx.particles>MAX_PARTICLES_TOTAL:_fail(path+".count",f"scene has more than {MAX_PARTICLES_TOTAL} particles in total")
        if "r" in layer:_num(layer["r"],path+".r",0.5,80)
        if "shape" in layer and layer["shape"] not in {"dot","ring","rbc"}:_fail(path+".shape","use dot, ring or rbc")
        if "speed" in layer:_num(layer["speed"],path+".speed",-5000,5000)
        if "spread" in layer:_num(layer["spread"],path+".spread",0,400)
        if "seed" in layer:_int(layer["seed"],path+".seed",0,2**31-1)
        if "size_jitter" in layer:_num(layer["size_jitter"],path+".size_jitter",0,1)
        if "phase" in layer:_num(layer["phase"],path+".phase",0,1)
        if "fade_ends" in layer:_bool(layer["fade_ends"],path+".fade_ends")
        if "guide" in layer:
            g=layer["guide"]
            if not isinstance(g,dict):_fail(path+".guide","guide must be an object")
            extra=set(g)-{"stroke","stroke_width","dash","opacity","fill"}
            if extra:_fail(path+".guide","unknown fields "+", ".join(sorted(extra)))
            for k in ("stroke","fill"):
                if k in g:_color(g[k],f"{path}.guide.{k}",ctx)
            if "stroke_width" in g:_num(g["stroke_width"],path+".guide.stroke_width",0,200)
            if "opacity" in g:_num(g["opacity"],path+".guide.opacity",0,1)
            if "dash" in g:
                if not isinstance(g["dash"],list) or not 1<=len(g["dash"])<=8 or not any(g["dash"]):_fail(path+".guide.dash","dash must be a list of 1..8 numbers, not all zero")
                for i,x in enumerate(g["dash"]):_num(x,f"{path}.guide.dash[{i}]",0,1000)
    if ltype=="spotlight":
        circle="r" in layer;box="width" in layer or "height" in layer
        if circle==box:_fail(path,"spotlight needs either cx/cy/r (circle) or x/y/width/height (box)")
        if box and not {"width","height"}<=set(layer):_fail(path,"box spotlight needs width and height")
        if "dim" in layer:_num(layer["dim"],path+".dim",0,1)
        if "color" in layer:_color(layer["color"],path+".color",ctx)
        geo=GEOMETRY_KEYS["spotlight"]-({"x","y","width","height"} if circle else {"cx","cy","r"})
        for i,k in enumerate(layer.get("keys",[])):
            bad=set(k)&(GEOMETRY_KEYS["spotlight"]-geo)
            if bad:_fail(f"{path}.keys[{i}]","this spotlight shape cannot animate "+", ".join(sorted(bad)))

def _validate_assets(assets,ctx:_Ctx):
    if not isinstance(assets,dict) or len(assets)>MAX_ASSETS:_fail("assets",f"assets must be an object with at most {MAX_ASSETS} entries")
    total=0
    for aid,uri in assets.items():
        p=f"assets.{aid}"
        if not ID_RE.fullmatch(str(aid)):_fail(p,"asset id must match ^[a-z][a-z0-9_-]{0,31}$")
        if not isinstance(uri,str):_fail(p,"asset must be a data URI string")
        m=re.fullmatch(r"data:image/(png|jpeg|webp|avif);base64,([A-Za-z0-9+/]+={0,2})",uri)
        if not m:_fail(p,"asset must be data:image/png|jpeg|webp|avif;base64,...")
        total+=len(uri)
        try:raw=base64.b64decode(m.group(2),validate=True)
        except (binascii.Error,ValueError):_fail(p,"asset base64 is invalid")
        if len(raw)>MAX_ASSET_BYTES:_fail(p,f"asset larger than {MAX_ASSET_BYTES} bytes; compress it (WebP recommended)")
        kind=m.group(1)
        ok={"png":raw.startswith(b"\x89PNG\r\n\x1a\n"),"jpeg":raw.startswith(b"\xff\xd8\xff"),"webp":raw[:4]==b"RIFF" and raw[8:12]==b"WEBP",
            "avif":raw[4:8]==b"ftyp" and raw[8:12] in (b"avif",b"avis")}[kind]
        if not ok:_fail(p,f"asset bytes are not a real {kind} image")
        ctx.assets.add(aid)
    if total>MAX_ASSET_CHARS_TOTAL:_fail("assets",f"assets exceed {MAX_ASSET_CHARS_TOTAL} characters in total")

def validate_scene_v2(scene:dict,duration_ms:int):
    extra=set(scene)-SCENE_V2_KEYS
    if extra:_fail("scene","unknown top-level fields "+", ".join(sorted(extra)))
    size=len(json.dumps(scene,ensure_ascii=False,separators=(",",":")).encode())
    if size>MAX_SCENE_BYTES:_fail("scene",f"scene JSON is {size} bytes; limit {MAX_SCENE_BYTES}")
    ctx=_Ctx(scene,duration_ms)
    stage=scene.get("stage",{})
    if not isinstance(stage,dict):_fail("stage","stage must be an object")
    extra=set(stage)-{"width","height","background"}
    if extra:_fail("stage","unknown fields "+", ".join(sorted(extra)))
    if "width" in stage:_num(stage["width"],"stage.width",240,1600)
    if "height" in stage:_num(stage["height"],"stage.height",240,1600)
    palette=scene.get("palette",{})
    if not isinstance(palette,dict) or len(palette)>40:_fail("palette","palette must be an object with at most 40 colours")
    for name,val in palette.items():
        if not TOKEN_NAME_RE.fullmatch(str(name)):_fail(f"palette.{name}","name must match ^[a-z][a-z0-9_]{0,23}$")
        if not isinstance(val,str) or not (HEX_RE.fullmatch(val) or RGB_RE.fullmatch(val) or HSL_RE.fullmatch(val)):_fail(f"palette.{name}","palette values must be #hex, rgb() or hsl()")
        ctx.tokens[name]=val
    grads=scene.get("gradients",[])
    if not isinstance(grads,list) or len(grads)>24:_fail("gradients","gradients must be a list of at most 24")
    for i,g in enumerate(grads):
        p=f"gradients[{i}]"
        if not isinstance(g,dict):_fail(p,"gradient must be an object")
        extra=set(g)-{"id","kind","stops","angle","cx","cy","r"}
        if extra:_fail(p,"unknown fields "+", ".join(sorted(extra)))
        if not isinstance(g.get("id"),str) or not ID_RE.fullmatch(g["id"]):_fail(p+".id","id must match ^[a-z][a-z0-9_-]{0,31}$")
        if g["id"] in ctx.gradients:_fail(p+".id","duplicate gradient id")
        if g.get("kind","linear") not in {"linear","radial"}:_fail(p+".kind","use linear or radial")
        if "angle" in g:_num(g["angle"],p+".angle",-360,360)
        for k in ("cx","cy","r"):
            if k in g:_num(g[k],f"{p}.{k}",0,2)
        stops=g.get("stops")
        if not isinstance(stops,list) or not 2<=len(stops)<=12:_fail(p+".stops","stops must be a list of 2..12")
        last=-1
        for j,s in enumerate(stops):
            sp=f"{p}.stops[{j}]"
            if not isinstance(s,dict) or set(s)-{"offset","color","opacity"} or "offset" not in s or "color" not in s:_fail(sp,"stop must be {offset, color, opacity?}")
            off=_num(s["offset"],sp+".offset",0,1)
            if off<last:_fail(sp+".offset","stop offsets must increase")
            last=off
            _color(s["color"],sp+".color",ctx)
            if str(s["color"]).startswith("url:"):_fail(sp+".color","a gradient stop cannot reference a gradient")
            if "opacity" in s:_num(s["opacity"],sp+".opacity",0,1)
        ctx.gradients.add(g["id"])
    if "background" in stage:_color(stage["background"],"stage.background",ctx)
    if "assets" in scene:_validate_assets(scene["assets"],ctx)
    cam=scene.get("camera")
    if cam is not None:
        if not isinstance(cam,dict) or set(cam)!={"keys"}:_fail("camera","camera must be {keys:[{t,x,y,zoom,ease}]}")
        keys=cam["keys"]
        if not isinstance(keys,list) or not 1<=len(keys)<=MAX_KEYS:_fail("camera.keys",f"camera needs 1..{MAX_KEYS} keys")
        last=-1
        for i,k in enumerate(keys):
            kp=f"camera.keys[{i}]"
            if not isinstance(k,dict) or set(k)-{"t","x","y","zoom","ease"} or "t" not in k:_fail(kp,"camera key must be {t, x?, y?, zoom?, ease?}")
            t=_int(k["t"],kp+".t",0,duration_ms)
            if t<last:_fail(kp+".t","keyframes must be in time order")
            last=t
            for c in ("x","y"):
                if c in k:_num(k[c],f"{kp}.{c}")
            if "zoom" in k:_num(k["zoom"],kp+".zoom",0.2,8)
            if "ease" in k:_ease(k["ease"],kp+".ease")
    if "credits" in scene:
        cr=scene["credits"]
        if not isinstance(cr,list) or not 1<=len(cr)<=12:_fail("credits","credits must be a list of 1..12 strings")
        for i,c in enumerate(cr):
            if not isinstance(c,str) or not c.strip() or len(c)>300:_fail(f"credits[{i}]","each credit must be a non-empty string of at most 300 characters")
    free="svg" in scene or "script" in scene
    if "svg" in scene:_validate_svg(scene["svg"],ctx)
    if "script" in scene:_validate_code(scene["script"],"script",MAX_SCRIPT_CHARS,r"\brender\b","must define function render(t, api)")
    layers=scene.get("layers",[] if free else None)
    lo=0 if free else 1
    if not isinstance(layers,list) or not lo<=len(layers)<=MAX_NODES:_fail("layers",f"layers must be a list of {lo}..{MAX_NODES}"+("" if free else " (or provide svg/script)"))
    ids=set()
    for i,layer in enumerate(layers):_validate_layer(layer,f"layers[{i}]",ctx,1,ids)
    if "custom_renderer" in scene:_validate_code(scene["custom_renderer"],"custom_renderer",MAX_CUSTOM_CHARS,r"function\s+renderCustom\s*\(","must define function renderCustom(layer,timeMs,helpers)")
    return scene

def _validate_code(code,path,limit,required,required_msg):
    if not isinstance(code,str) or not code.strip():_fail(path,"must be a non-empty string")
    if len(code)>limit:_fail(path,f"longer than {limit} characters")
    m=SCRIPT_BREAKERS.search(code)
    if m:
        line=code.count("\n",0,m.start())+1
        _fail(path,f"line {line}: {m.group(0)!r} would end the page's script element; write it as '<\\/script' or split the string")
    if not re.search(required,code):_fail(path,required_msg)

def _validate_svg(svg,ctx:_Ctx):
    if not isinstance(svg,str) or not svg.strip():_fail("svg","must be a non-empty SVG string")
    if len(svg)>MAX_SVG_CHARS:_fail("svg",f"longer than {MAX_SVG_CHARS} characters")
    if re.search(r"<!DOCTYPE|<!ENTITY",svg,re.I):_fail("svg","remove <!DOCTYPE>/<!ENTITY> declarations")
    try:root=ET.fromstring(svg)
    except ET.ParseError as exc:
        line,col=getattr(exc,"position",(0,0))
        _fail("svg",f"not well-formed XML at line {line}, column {col+1}: {exc}")
    if root.tag not in {"svg",SVG_NS+"svg"}:_fail("svg","root element must be <svg>")
    for el in root.iter():
        tag=el.tag.split("}")[-1]
        if tag=="script":_fail("svg","<script> inside svg is not run; put code in scene.script")
        if tag=="style" and el.text and re.search(r"@import|url\(\s*['\"]?\s*(?:https?:)?//",el.text,re.I):_fail("svg","<style> loads external CSS, which is blocked in production")
        for key,val in el.attrib.items():
            name=key.split("}")[-1]
            if name in {"href","src"}:
                if val.startswith("asset:"):
                    aid=val[6:]
                    if aid not in ctx.assets:_fail("svg",f"<{tag} {name}=\"{val}\">: unknown asset id (declare it in scene.assets)")
                    ctx.used_assets.add(aid)
                elif EXTERNAL_REF.match(val):_fail("svg",f"<{tag} {name}=\"{val[:60]}\">: external URLs are blocked in production; embed the image in scene.assets and use href=\"asset:<id>\"")
            if re.search(r"url\(\s*['\"]?\s*(?:https?:)?//",val,re.I):_fail("svg",f"<{tag} {name}>: external url() is blocked in production")
            if isinstance(val,str) and val.startswith("@") and name in {"fill","stroke","stop-color","flood-color","color"}:
                if val[1:] not in ctx.tokens:_fail("svg",f"<{tag} {name}=\"{val}\">: unknown colour token")

def lint_scene_v2(scene:dict)->list[str]:
    """Non-fatal layout warnings: things that are valid but usually look bad."""
    warnings=[];stage=scene.get("stage") or {};W=stage.get("width",640);H=stage.get("height",560)
    used=set(re.findall(r'href="asset:([a-z][a-z0-9_-]{0,31})"',str(scene.get("svg") or "")))   # assets drawn by the free-mode svg
    def walk(layers,path,ox,oy):
        for i,l in enumerate(layers):
            p=f"{path}[{i}]";t=l.get("type")
            if t=="group":walk(l.get("layers",[]),p+".layers",ox+l.get("x",0),oy+l.get("y",0));continue
            if t=="image":used.add(l.get("asset"))
            if t in {"text","label"}:
                size=l.get("size",24);text=str(l.get("text",""))
                if size<13:warnings.append(f"{p}: text size {size} is hard to read on phones (use >= 14)")
                if "max_width" not in l:
                    est=max(len(x) for x in text.split("\n"))*size*0.55
                    if est>W*0.9:warnings.append(f"{p}: text is about {int(est)}px wide on a {W}px stage; add max_width")
                    x=ox+l.get("x",0);a=l.get("anchor","middle")
                    left=x-est/2 if a=="middle" else (x if a=="start" else x-est)
                    if left<0 or left+est>W:warnings.append(f"{p}: text probably runs off the stage edge; add max_width or move it")
                y=oy+l.get("y",0)
                if y<0 or y>H:warnings.append(f"{p}: text y={y} is outside the stage")
            if t=="circle":
                cx=ox+l.get("cx",0);cy=oy+l.get("cy",0);r=l.get("r",0)
                if cx+r<0 or cx-r>W or cy+r<0 or cy-r>H:warnings.append(f"{p}: circle is completely off stage")
            if t in {"rect","highlight","focus"}:
                x=ox+l.get("x",0);y=oy+l.get("y",0)
                if x>W or y>H or x+l.get("width",0)<0 or y+l.get("height",0)<0:warnings.append(f"{p}: rect is completely off stage")
            show=l.get("show")
            if isinstance(show,list) and len(show)==2 and show[1]-show[0]<300:warnings.append(f"{p}: visible for only {show[1]-show[0]} ms")
    walk(scene.get("layers",[]),"layers",0,0)
    def visible_at_zero(l):
        if isinstance(l.get("show"),list) and l["show"][0]>0:return False
        e=l.get("enter");name=e if isinstance(e,str) else (e or {}).get("effect")
        if name and name!="none":return False
        if l.get("opacity",1)==0:return False
        return True
    code=str(scene.get("script") or "")+str(scene.get("custom_renderer") or "")
    if re.search(r"\bDate\.now\b|\bperformance\.now\b|\bnew Date\b",code):
        warnings.append("script uses the wall clock (Date/performance.now); frames must depend only on t or pause/seek will look wrong")
    if "Math.random" in code:
        warnings.append("Math.random is seeded, but every call returns a new value: draw random numbers once in setup(api) (or use api.random(seed)), never inside render()")
    for c in scene.get("credits") or []:
        if re.search(r"\b(?:CC[\s-]*)?BY[\s-]*(?:NC|ND)\b|non[\s-]?commercial|no[\s-]?derivatives?",str(c),re.I):
            warnings.append(f"credit {c!r} names an NC/ND licence; that material may not be used in MotionCards")
    def complex_morphs(layers,path):
        for i,l in enumerate(layers):
            if l.get("type")=="group":complex_morphs(l.get("layers",[]),f"{path}[{i}].layers");continue
            if l.get("type")=="path" and any("d" in k for k in l.get("keys",[])) and len(PATH_NUM_RE.findall(str(l.get("d",""))))>60:
                warnings.append(f"{path}[{i}]: morphing a complex path; organic morphs usually look wrong, so cross-fade two drawings instead")
    complex_morphs(scene.get("layers",[]),"layers")
    if re.search(r"https?://(?!www\.w3\.org/)",code):
        warnings.append("script mentions an external URL; network access is blocked in production")
    if "svg" in scene or "script" in scene:pass
    elif not any(visible_at_zero(l) for l in scene.get("layers",[])):
        warnings.append("first frame (t=0) is empty: the app shows this frame before Play, so keep the main structure visible at t=0 (no enter effect)")
    for aid in (scene.get("assets") or {}):
        if aid not in used:warnings.append(f"assets.{aid}: declared but never used (adds size)")
    if re.search(r"\bR\.grid\(",str(scene.get("script") or "")):warnings.append("script: R.grid(api) is a layout aid; remove it before packaging")
    return warnings

RUNTIME_V2_JS=r"""(()=>{"use strict";
const CONFIG=__MC_BOOT.config,root=document.getElementById('root'),AUTHOR_LINE=__MC_AUTHOR_LINE__;
const hashChannel=location.hash.slice(1);
if(!/^[a-f0-9]{36}$/.test(hashChannel))throw new Error('motioncards_channel_invalid');
CONFIG.channel_id=hashChannel;
const MC={protocol:1,qid:CONFIG.qid,duration:CONFIG.duration_ms,port:null,destroyed:false,broken:null};
const NS='http://www.w3.org/2000/svg',SC=CONFIG.scene,D=CONFIG.duration_ms;
const W=Number((SC.stage||{}).width||640),H=Number((SC.stage||{}).height||560);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const lerp=(a,b,p)=>a+(b-a)*p;
const EASE={linear:p=>p,ease_in:p=>p*p*p,ease_out:p=>1-Math.pow(1-p,3),ease_in_out:p=>p<.5?4*p*p*p:1-Math.pow(-2*p+2,3)/2,
 sine:p=>-(Math.cos(Math.PI*p)-1)/2,back_out:p=>{const c=1.70158;return 1+(c+1)*Math.pow(p-1,3)+c*Math.pow(p-1,2);},
 back_in:p=>{const c=1.70158;return (c+1)*p*p*p-c*p*p;},
 elastic_out:p=>p<=0?0:p>=1?1:Math.pow(2,-10*p)*Math.sin((p*10-.75)*(2*Math.PI/3))+1,
 bounce_out:p=>{const n=7.5625,d=2.75;if(p<1/d)return n*p*p;if(p<2/d)return n*(p-=1.5/d)*p+.75;if(p<2.5/d)return n*(p-=2.25/d)*p+.9375;return n*(p-=2.625/d)*p+.984375;},
 step:p=>p<1?0:1};
const ease=(name,p)=>(EASE[name]||EASE.ease_in_out)(clamp(p,0,1));
const TOKENS=Object.assign({},CONFIG.tokens,SC.palette||{});
const FONTS={sans:'system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Sans Arabic",Arial,sans-serif',serif:'Georgia,"Times New Roman","Noto Serif",serif',mono:'ui-monospace,Menlo,Consolas,monospace',rounded:'ui-rounded,"SF Pro Rounded",Nunito,"Varela Round",system-ui,sans-serif'};
const PNUM=/-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g;
function color(c){if(typeof c!=='string')return c;if(c[0]==='@')return TOKENS[c.slice(1)]||'#000';if(c.startsWith('url:'))return 'url(#mcg-'+c.slice(4)+')';return c;}
function hsl2rgb(h,s,l){h=((h%360)+360)%360/360;s/=100;l/=100;if(!s)return[l*255,l*255,l*255];const q=l<.5?l*(1+s):l+s-l*s,p=2*l-q,f=t=>{t=(t+1)%1;return 255*(t<1/6?p+(q-p)*6*t:t<.5?q:t<2/3?p+(q-p)*(2/3-t)*6:p);};return[f(h+1/3),f(h),f(h-1/3)];}
function parseColor(c){
 c=color(c);let m;
 if(/^#[0-9a-f]+$/i.test(c)){let h=c.slice(1);if(h.length<5)h=h.split('').map(x=>x+x).join('');return[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16),h.length>6?parseInt(h.slice(6,8),16)/255:1];}
 if((m=/^rgba?\(([^)]*)\)$/.exec(c))){const v=m[1].split(',').map(Number);return[v[0],v[1],v[2],v.length>3?v[3]:1];}
 if((m=/^hsla?\(([^)]*)\)$/.exec(c))){const v=m[1].split(',').map(x=>parseFloat(x));const r=hsl2rgb(v[0],v[1],v[2]);return[r[0],r[1],r[2],v.length>3?v[3]:1];}
 return[0,0,0,1];
}
function mk(tag,attrs,parent){const e=document.createElementNS(NS,tag);if(attrs)for(const k in attrs){const v=attrs[k];if(v!==undefined&&v!==null)e.setAttribute(k,String(v));}if(parent)parent.appendChild(e);return e;}
function setA(e,k,v){const s=String(v);if(e.getAttribute(k)!==s)e.setAttribute(k,s);}
function fmt(n){return Math.round(n*1000)/1000;}
function rand(seed){let a=seed>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
const svg=document.getElementById('stage');
svg.setAttribute('viewBox','0 0 '+W+' '+H);
const defs=mk('defs',null,svg),guides=mk('g',{visibility:'hidden','aria-hidden':'true'},svg);
const bg=mk('rect',{x:-W*4,y:-H*4,width:W*9,height:H*9,fill:color((SC.stage||{}).background||'#fbfaf7')},svg);
const cam=mk('g',null,svg),hud=mk('g',null,svg),customLayer=mk('g',null,svg);
for(const g of SC.gradients||[]){
 let el;
 if(g.kind==='radial')el=mk('radialGradient',{id:'mcg-'+g.id,cx:g.cx??.5,cy:g.cy??.5,r:g.r??.5},defs);
 else{const a=(g.angle??90)*Math.PI/180,c=Math.cos(a)/2,s=Math.sin(a)/2;el=mk('linearGradient',{id:'mcg-'+g.id,x1:fmt(.5-c),y1:fmt(.5-s),x2:fmt(.5+c),y2:fmt(.5+s)},defs);}
 for(const s of g.stops)mk('stop',{offset:s.offset,'stop-color':color(s.color),'stop-opacity':s.opacity??1},el);
}
const filters={};let filterCount=0;
function filterFor(L){
 const sh=L.shadow===true?'soft':(L.shadow||''),gl=L.glow||'',bl=Number(L.blur||0);
 if(!sh&&!gl&&!bl)return null;
 const key=sh+'|'+gl+'|'+bl;if(filters[key])return filters[key];
 const id='mcf-'+(filterCount++),f=mk('filter',{id,x:'-40%',y:'-40%',width:'180%',height:'180%','color-interpolation-filters':'sRGB'},defs);
 if(bl)mk('feGaussianBlur',{stdDeviation:bl},f);
 if(gl)mk('feDropShadow',{dx:0,dy:0,stdDeviation:6,'flood-color':color(gl),'flood-opacity':.85},f);
 if(sh==='soft')mk('feDropShadow',{dx:0,dy:3,stdDeviation:4,'flood-color':'#0b1b26','flood-opacity':.22},f);
 if(sh==='strong')mk('feDropShadow',{dx:0,dy:7,stdDeviation:9,'flood-color':'#0b1b26','flood-opacity':.34},f);
 return filters[key]='url(#'+id+')';
}
function lut(d){
 const p=mk('path',{d},guides),len=p.getTotalLength()||0,n=Math.max(2,Math.min(2000,Math.ceil(len/2)+1)),pts=new Float64Array(n*2);
 for(let i=0;i<n;i++){const q=p.getPointAtLength(len*i/(n-1));pts[i*2]=q.x;pts[i*2+1]=q.y;}
 return{len,n,pts};
}
function at(L,s){
 if(L.len<=0)return[L.pts[0],L.pts[1],0];
 const f=clamp(s/L.len,0,1)*(L.n-1),i=Math.min(L.n-2,Math.floor(f)),u=f-i,x0=L.pts[i*2],y0=L.pts[i*2+1],x1=L.pts[i*2+2],y1=L.pts[i*2+3];
 return[x0+(x1-x0)*u,y0+(y1-y0)*u,Math.atan2(y1-y0,x1-x0)*180/Math.PI];
}
function prep(prop,v){
 if(prop==='fill'||prop==='stroke')return{c:parseColor(v)};
 if(prop==='d'){const n=(String(v).match(PNUM)||[]).map(Number);return{n};}
 return v;
}
function mix(a,b,p){
 if(typeof a==='number')return a+(b-a)*p;
 if(a&&a.c)return{c:a.c.map((x,i)=>x+(b.c[i]-x)*p)};
 if(a&&a.n)return{n:a.n.map((x,i)=>x+(b.n[i]-x)*p)};
 return p<1?a:b;
}
function sample(tr,t){
 if(t<=tr[0].t)return tr[0].v;const last=tr[tr.length-1];if(t>=last.t)return last.v;
 for(let i=1;i<tr.length;i++){const b=tr[i];if(t<=b.t){const a=tr[i-1],span=b.t-a.t;return mix(a.v,b.v,span<=0?1:ease(b.e,(t-a.t)/span));}}
 return last.v;
}
function cssColor(v){if(v&&v.c){const c=v.c;return 'rgba('+Math.round(clamp(c[0],0,255))+','+Math.round(clamp(c[1],0,255))+','+Math.round(clamp(c[2],0,255))+','+fmt(clamp(c[3],0,1))+')';}return color(v);}
function effectOf(e,dflt){if(!e)return null;if(typeof e==='string')return{effect:e,ms:dflt,ease:null};return{effect:e.effect,ms:e.ms??dflt,ease:e.ease||null};}
const DEF_FILL={rect:'@surface',circle:'@surface',ellipse:'@surface',polygon:'@surface',highlight:'@highlight',focus:'none',path:'none',line:'none',polyline:'none',arrow:'none',particles:'@blood'};
const DEF_STROKE={rect:'none',circle:'none',ellipse:'none',polygon:'none',highlight:'none',focus:'@accent',path:'@ink',line:'@ink',polyline:'@ink',arrow:'@ink',particles:'none'};
const DEF_SW={focus:4,path:3,line:3,polyline:3,arrow:6,rect:2,circle:2,ellipse:2,polygon:2,highlight:0,particles:1};
const nodes=[];
function paint(el,L,type){
 const fill=L.fill??DEF_FILL[type],stroke=L.stroke??DEF_STROKE[type];
 el.setAttribute('fill',color(fill));el.setAttribute('stroke',color(stroke));el.setAttribute('stroke-width',L.stroke_width??DEF_SW[type]??2);
 if(L.fill_opacity!=null)el.setAttribute('fill-opacity',L.fill_opacity);else if(type==='highlight')el.setAttribute('fill-opacity',.55);
 if(L.stroke_opacity!=null)el.setAttribute('stroke-opacity',L.stroke_opacity);
 if(L.dash)el.setAttribute('stroke-dasharray',L.dash.join(' '));else if(type==='focus')el.setAttribute('stroke-dasharray','10 8');
 el.setAttribute('stroke-linecap',L.linecap||'round');el.setAttribute('stroke-linejoin',L.linejoin||'round');
}
function arrowGeom(n,g){
 const x1=g.x1,y1=g.y1,x2=g.x2,y2=g.y2,b=g.bend||0,mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy)||1;
 const cx=mx-dy/len*b,cy=my+dx/len*b,hs=n.L.head_size??Math.max(12,(n.sw||6)*2.6),head=n.L.head||'end';
 const tip=(px,py,ax,ay)=>{const ux=px-ax,uy=py-ay,l=Math.hypot(ux,uy)||1,vx=ux/l,vy=uy/l,bx=px-vx*hs,by=py-vy*hs,w=hs*.55;return 'M '+fmt(px)+' '+fmt(py)+' L '+fmt(bx-vy*w)+' '+fmt(by+vx*w)+' L '+fmt(bx+vy*w)+' '+fmt(by-vx*w)+' Z';};
 const trimEnd=(head==='end'||head==='both')?hs*.8:0,trimStart=(head==='start'||head==='both')?hs*.8:0;
 const ex=x2-(x2-cx)/(Math.hypot(x2-cx,y2-cy)||1)*trimEnd,ey=y2-(y2-cy)/(Math.hypot(x2-cx,y2-cy)||1)*trimEnd;
 const sx=x1+(cx-x1)/(Math.hypot(cx-x1,cy-y1)||1)*trimStart,sy=y1+(cy-y1)/(Math.hypot(cx-x1,cy-y1)||1)*trimStart;
 setA(n.shaft,'d','M '+fmt(sx)+' '+fmt(sy)+' Q '+fmt(cx)+' '+fmt(cy)+' '+fmt(ex)+' '+fmt(ey));
 setA(n.heads,'d',(head==='end'||head==='both'?tip(x2,y2,cx,cy):'')+(head==='start'||head==='both'?' '+tip(x1,y1,cx,cy):'')||'M 0 0');
}
function spotD(g,circle){
 const outer='M '+(-W*4)+' '+(-H*4)+' H '+(W*5)+' V '+(H*5)+' H '+(-W*4)+' Z ';
 if(circle){const r=Math.max(0,g.r);return outer+'M '+fmt(g.cx-r)+' '+fmt(g.cy)+' a '+fmt(r)+' '+fmt(r)+' 0 1 0 '+fmt(2*r)+' 0 a '+fmt(r)+' '+fmt(r)+' 0 1 0 '+fmt(-2*r)+' 0 Z';}
 const x=g.x,y=g.y,w=Math.max(0,g.width),h=Math.max(0,g.height),r=Math.min(g.rx||0,w/2,h/2);
 return outer+'M '+fmt(x+r)+' '+fmt(y)+' H '+fmt(x+w-r)+' Q '+fmt(x+w)+' '+fmt(y)+' '+fmt(x+w)+' '+fmt(y+r)+' V '+fmt(y+h-r)+' Q '+fmt(x+w)+' '+fmt(y+h)+' '+fmt(x+w-r)+' '+fmt(y+h)+' H '+fmt(x+r)+' Q '+fmt(x)+' '+fmt(y+h)+' '+fmt(x)+' '+fmt(y+h-r)+' V '+fmt(y+r)+' Q '+fmt(x)+' '+fmt(y)+' '+fmt(x+r)+' '+fmt(y)+' Z';
}
function layoutText(n){
 const L=n.L,t=n.text,maxW=L.max_width,lh=L.line_height||1.25;let size=L.size||24;
 const paras=String(L.text).split('\n');
 const measure=s=>{const k=mk('tspan',null,t);k.textContent=s;const w=k.getComputedTextLength();t.removeChild(k);return w;};
 const wrap=()=>{t.setAttribute('font-size',size);if(!maxW)return paras;const out=[];for(const para of paras){const words=para.split(/\s+/).filter(Boolean);let line='';for(const w of words){const tryLine=line?line+' '+w:w;if(line&&measure(tryLine)>maxW){out.push(line);line=w;}else line=tryLine;}out.push(line);}return out;};
 let lines=wrap();
 if(L.fit&&maxW){for(let i=0;i<10;i++){const widest=Math.max(...lines.map(measure));const tooMany=L.max_lines&&lines.length>L.max_lines;if(widest<=maxW+.5&&!tooMany)break;size=Math.max(6,tooMany?size*.9:size*Math.min(.97,maxW/widest));lines=wrap();}}
 n.lines=lines;n.total=lines.reduce((a,s)=>a+s.length,0);n.size=size;
 const y0=(L.y||0)-(lines.length-1)*size*lh/2;
 n.spans=lines.map((s,i)=>{const k=mk('tspan',{x:L.x||0,y:fmt(y0+i*size*lh)},t);k.textContent=s;return k;});
 if(L.box){const b=t.getBBox(),pad=L.box.pad??Math.round(size*.45);const r=mk('rect',{x:fmt(b.x-pad),y:fmt(b.y-pad*.7),width:fmt(b.width+pad*2),height:fmt(b.height+pad*1.4),rx:L.box.rx??Math.round(size*.6),fill:color(L.box.fill||'@paper'),stroke:color(L.box.stroke||'none'),'stroke-width':L.box.stroke_width??1.5,opacity:L.box.opacity??1},null);n.body.insertBefore(r,t);}
}
function build(L,parent,depth){
 const type=L.type==='label'?'text':L.type,w=mk('g',null,parent),body=mk('g',null,w);
 const n={L,type,w,body,tracks:{},children:[],show:L.show||[0,D],geo:{}};
 const f=filterFor(L);if(f)w.setAttribute('filter',f);
 const usesDraw=(L.keys||[]).some(k=>'draw' in k)||[L.enter,L.exit].some(e=>e==='draw'||(e&&e.effect==='draw'));
 const geoKeys=new Set();for(const k of L.keys||[])for(const p in k)geoKeys.add(p);
 if(type==='rect'||type==='highlight'||type==='focus'){n.shape=mk('rect',{x:L.x||0,y:L.y||0,width:L.width,height:L.height,rx:L.rx??12},body);paint(n.shape,L,type);n.geo={width:L.width,height:L.height,rx:L.rx??12};}
 else if(type==='circle'){n.shape=mk('circle',{cx:L.cx||0,cy:L.cy||0,r:L.r},body);paint(n.shape,L,type);n.geo={cx:L.cx||0,cy:L.cy||0,r:L.r};}
 else if(type==='ellipse'){n.shape=mk('ellipse',{cx:L.cx||0,cy:L.cy||0,rx:L.rx,ry:L.ry},body);paint(n.shape,L,type);n.geo={cx:L.cx||0,cy:L.cy||0,rx:L.rx,ry:L.ry};}
 else if(type==='line'){n.shape=mk('line',{x1:L.x1,y1:L.y1,x2:L.x2,y2:L.y2},body);paint(n.shape,L,type);n.geo={x1:L.x1,y1:L.y1,x2:L.x2,y2:L.y2};}
 else if(type==='path'){n.shape=mk('path',{d:L.d},body);paint(n.shape,L,type);n.tpl=String(L.d).split(PNUM);n.geo={d:prep('d',L.d)};}
 else if(type==='polygon'||type==='polyline'){n.shape=mk(type,{points:L.points.map(p=>p[0]+','+p[1]).join(' ')},body);paint(n.shape,L,type);}
 else if(type==='arrow'){
  n.sw=L.stroke_width??6;n.shape=n.shaft=mk('path',null,body);paint(n.shaft,L,'arrow');n.shaft.setAttribute('fill','none');
  n.heads=mk('path',{fill:color(L.stroke??'@ink'),stroke:'none'},body);if(L.stroke_opacity!=null)n.heads.setAttribute('fill-opacity',L.stroke_opacity);
  n.geo={x1:L.x1,y1:L.y1,x2:L.x2,y2:L.y2,bend:L.bend||0};arrowGeom(n,n.geo);
 }
 else if(type==='text'){
  n.text=mk('text',{'text-anchor':L.anchor||'middle','dominant-baseline':'central','font-family':FONTS[L.font||'sans'],'font-weight':L.weight??600,fill:color(L.color??L.fill??'@ink')},body);
  if(L.italic)n.text.setAttribute('font-style','italic');if(L.letter_spacing!=null)n.text.setAttribute('letter-spacing',L.letter_spacing);
  if(/[\u0590-\u08FF]/.test(String(L.text))){n.text.setAttribute('direction','rtl');n.text.setAttribute('unicode-bidi','plaintext');}
  if(L.halo){n.text.setAttribute('stroke',color(L.halo));n.text.setAttribute('stroke-width',Math.max(2,(L.size||24)*.18));n.text.setAttribute('stroke-linejoin','round');n.text.setAttribute('paint-order','stroke');}
  layoutText(n);n.shape=n.text;
 }
 else if(type==='image'){
  const fit=L.fit||'contain';n.shape=mk('image',{x:L.x||0,y:L.y||0,width:L.width,height:L.height,preserveAspectRatio:fit==='stretch'?'none':fit==='cover'?'xMidYMid slice':'xMidYMid meet'},body);
  n.shape.setAttribute('href',SC.assets[L.asset]);
  if(fit==='cover'){const id='mcc-'+nodes.length,cp=mk('clipPath',{id},defs);mk('rect',{x:L.x||0,y:L.y||0,width:L.width,height:L.height},cp);n.shape.setAttribute('clip-path','url(#'+id+')');}
 }
 else if(type==='group'){if(L.x||L.y)body.setAttribute('transform','translate('+(L.x||0)+' '+(L.y||0)+')');for(const c of L.layers)n.children.push(build(c,body,depth+1));}
 else if(type==='particles'){
  const g=L.guide;n.track=lut(L.d);
  if(g){const gp=mk('path',{d:L.d,fill:color(g.fill||'none'),stroke:color(g.stroke||'@line'),'stroke-width':g.stroke_width??2,opacity:g.opacity??1,'stroke-linecap':'round'},body);if(g.dash)gp.setAttribute('stroke-dasharray',g.dash.join(' '));}
  const R=rand((L.seed??7)*7919+13),count=L.count??24,r=L.r??5,shape=L.shape||'dot',jit=L.size_jitter??.25,spread=L.spread??0;
  n.parts=[];n.speed=L.speed??80;n.geo={speed:n.speed};
  for(let i=0;i<count;i++){
   const pr=r*(1-jit*R()),off=(R()-.5)*spread,ph=((i+R()*.6)/count+(L.phase||0))%1,pg=mk('g',null,body);let el;
   if(shape==='rbc'){el=mk('ellipse',{rx:fmt(pr),ry:fmt(pr*.72)},pg);mk('ellipse',{rx:fmt(pr*.45),ry:fmt(pr*.28),fill:'#000','fill-opacity':.14},pg);}
   else el=mk('circle',{r:fmt(pr)},pg);
   paint(el,L,'particles');if(shape==='ring'){el.setAttribute('fill','none');el.setAttribute('stroke',color(L.stroke??L.fill??'@blood'));el.setAttribute('stroke-width',L.stroke_width??Math.max(1.5,pr*.35));}
   n.parts.push({g:pg,el,off,ph});
  }
  n.shape=null;
 }
 else if(type==='spotlight'){
  n.circle=L.r!=null;n.geo=n.circle?{cx:L.cx??W/2,cy:L.cy??H/2,r:L.r}:{x:L.x||0,y:L.y||0,width:L.width,height:L.height,rx:L.rx??18};n.geo.dim=L.dim??.6;
  n.shape=mk('path',{'fill-rule':'evenodd',fill:color(L.color||'#0b1b26')},body);setA(n.shape,'d',spotD(n.geo,n.circle));n.shape.setAttribute('fill-opacity',n.geo.dim);
 }
 if(usesDraw&&n.shape)n.shape.setAttribute('pathLength','1');
 if(L.along)n.along=lut(L.along.d);
 for(const k of L.keys||[])for(const p in k){if(p==='t'||p==='ease')continue;(n.tracks[p]=n.tracks[p]||[]).push({t:k.t,v:prep(p,k[p]),e:k.ease||'ease_in_out'});}
 const o=L.origin;
 if(Array.isArray(o))n.origin=o;
 else{let b={x:0,y:0,width:0,height:0};try{b=body.getBBox();}catch(_){}n.origin=[b.x+b.width/2+(type==='group'?(L.x||0):0),b.y+b.height/2+(type==='group'?(L.y||0):0)];}
 if(n.along)n.anchor=n.origin;
 n.enter=effectOf(L.enter,type==='text'&&(L.enter==='type'||(L.enter&&L.enter.effect==='type'))?Math.min(1800,Math.max(400,String(L.text).length*35)):450);
 n.exit=effectOf(L.exit,350);
 nodes.push(n);return n;
}
const roots=[];
const camTrack=[];for(const k of (SC.camera||{}).keys||[])for(const p of ['x','y','zoom'])if(p in k)(camTrack[p]=camTrack[p]||[]).push({t:k.t,v:k[p],e:k.ease||'ease_in_out'});
function fxOf(eff,p,entering,n){
 const out={o:1,dx:0,dy:0,s:1,draw:1,type:1};if(!eff||eff.effect==='none')return out;
 const q=ease(eff.ease||(entering?'ease_out':'ease_in'),p),k=entering?q:1-q,d=24;
 switch(eff.effect){
  case 'fade':out.o=k;break;
  case 'pop':out.o=clamp(k*1.6,0,1);out.s=entering?.6+.4*ease(eff.ease||'back_out',p):.6+.4*k;break;
  case 'grow':out.s=k;out.o=clamp(k*3,0,1);break;
  case 'shrink':out.s=k;out.o=clamp(k*3,0,1);break;
  case 'draw':out.draw=k;break;
  case 'type':out.type=k;break;
  case 'slide_up':out.dy=(1-k)*d*(entering?1:-1);out.o=k;break;
  case 'slide_down':out.dy=-(1-k)*d*(entering?1:-1);out.o=k;break;
  case 'slide_left':out.dx=(1-k)*d*(entering?1:-1);out.o=k;break;
  case 'slide_right':out.dx=-(1-k)*d*(entering?1:-1);out.o=k;break;
 }
 return out;
}
function localTime(n,t){
 const r=n.L.repeat;if(!r)return t;
 const from=r.from_ms??n.show[0],every=r.every_ms;if(t<from)return 0;
 const k=(t-from)/every;if(r.times&&k>=r.times)return every;return (t-from)%every;
}
function particlesDistance(n,t){
 const s=n.show[0],tr=n.tracks.speed;if(!tr)return n.speed*(t-s)/1000;
 const steps=Math.max(1,Math.min(600,Math.ceil((t-s)/40)));let dist=0,prev=sample(tr,localTime(n,s));
 for(let i=1;i<=steps;i++){const tt=s+(t-s)*i/steps,v=sample(tr,localTime(n,tt));dist+=(prev+v)/2*((t-s)/steps)/1000;prev=v;}
 return dist;
}
function update(n,t){
 const L=n.L,vis=t>=n.show[0]&&t<=n.show[1];
 if(!vis){setA(n.w,'display','none');return;}
 setA(n.w,'display','inline');
 const lt=localTime(n,t),v=p=>n.tracks[p]?sample(n.tracks[p],lt):undefined;
 const span=n.show[1]-n.show[0];
 let fx={o:1,dx:0,dy:0,s:1,draw:1,type:1};
 if(n.enter){const ms=Math.min(n.enter.ms,span);const p=ms>0?(t-n.show[0])/ms:1;if(p<1)fx=fxOf(n.enter,clamp(p,0,1),true,n);}
 if(n.exit&&n.show[1]<D){const ms=Math.min(n.exit.ms,span);const p=ms>0?(t-(n.show[1]-ms))/ms:0;if(p>0){const e=fxOf(n.exit,clamp(p,0,1),false,n);fx={o:fx.o*e.o,dx:fx.dx+e.dx,dy:fx.dy+e.dy,s:fx.s*e.s,draw:Math.min(fx.draw,e.draw),type:fx.type};}}
 const op=clamp((v('opacity')??L.opacity??1)*fx.o,0,1);
 let tx=(v('x')??0)+fx.dx,ty=(v('y')??0)+fx.dy,rot=v('rotate')??0;
 const sc=(v('scale')??1)*fx.s,sx=sc*(v('scale_x')??1),sy=sc*(v('scale_y')??1);
 if(n.along){const pr=clamp(v('progress')??0,0,1),pt=at(n.along,pr*n.along.len);tx+=pt[0]-n.anchor[0];ty+=pt[1]-n.anchor[1];if(L.along.rotate)rot+=pt[2];}
 const ox=n.origin[0],oy=n.origin[1];
 setA(n.w,'opacity',fmt(op));
 setA(n.w,'transform','translate('+fmt(tx+ox)+' '+fmt(ty+oy)+') rotate('+fmt(rot)+') scale('+fmt(sx)+' '+fmt(sy)+') translate('+fmt(-ox)+' '+fmt(-oy)+')');
 if(n.shape){
  const fill=v('fill'),stroke=v('stroke'),sw=v('stroke_width');
  if(fill!==undefined)setA(n.shape,'fill',cssColor(fill));
  if(stroke!==undefined){setA(n.shape,'stroke',cssColor(stroke));if(n.heads)setA(n.heads,'fill',cssColor(stroke));}
  if(sw!==undefined)setA(n.shape,'stroke-width',fmt(sw));
  const dr=Math.min(clamp(v('draw')??1,0,1),fx.draw);
  if(n.shape.getAttribute('pathLength')){
   const so=L.stroke_opacity??1,fo=L.fill_opacity??(n.type==='highlight'?.55:1);
   if(dr<1){setA(n.shape,'stroke-dasharray',fmt(dr)+' 1.001');setA(n.shape,'stroke-dashoffset','0');setA(n.shape,'stroke-opacity',dr<=.001?'0':String(so));setA(n.shape,'fill-opacity',fmt(fo*clamp((dr-.7)/.3,0,1)));}
   else{setA(n.shape,'stroke-opacity',String(so));setA(n.shape,'fill-opacity',String(fo));if(L.dash)setA(n.shape,'stroke-dasharray',L.dash.join(' '));else if(n.type==='focus')setA(n.shape,'stroke-dasharray','10 8');else if(n.shape.hasAttribute('stroke-dasharray'))n.shape.removeAttribute('stroke-dasharray');}
   if(n.heads)setA(n.heads,'opacity',fmt(clamp((dr-.85)/.15,0,1)));
  }
 }
 const g={};let geoChanged=false;
 for(const k in n.geo){const val=n.tracks[k]?sample(n.tracks[k],lt):n.geo[k];g[k]=val;if(n.tracks[k])geoChanged=true;}
 if(geoChanged){
  if(n.type==='arrow')arrowGeom(n,g);
  else if(n.type==='path')setA(n.shape,'d',n.tpl.map((s,i)=>i<g.d.n.length?s+fmt(g.d.n[i]):s).join(''));
  else if(n.type==='spotlight'){setA(n.shape,'d',spotD(g,n.circle));setA(n.shape,'fill-opacity',fmt(clamp(g.dim,0,1)));}
  else if(n.type!=='particles')for(const k in g)setA(n.shape,k,fmt(['cx','cy','x1','y1','x2','y2'].includes(k)?g[k]:Math.max(0,g[k])));
 }
 if(n.type==='text'&&n.spans){
  const fillT=v('fill');if(fillT!==undefined)setA(n.text,'fill',cssColor(fillT));
  let left=fx.type<1?Math.round(n.total*fx.type):n.total;
  n.lines.forEach((s,i)=>{const show=s.slice(0,Math.max(0,left));left-=s.length;if(n.spans[i].textContent!==show)n.spans[i].textContent=show;});
 }
 if(n.type==='particles'){
  const fillP=v('fill'),strokeP=v('stroke');
  const dist=particlesDistance(n,t),len=n.track.len,fade=L.fade_ends!==false;
  for(const p of n.parts){
   if(fillP!==undefined&&L.shape!=='ring')setA(p.el,'fill',cssColor(fillP));
   if(strokeP!==undefined)setA(p.el,'stroke',cssColor(strokeP));
   if(len<=0){setA(p.g,'opacity','0');continue;}
   const s=(((p.ph*len+dist)%len)+len)%len,pt=at(n.track,s),a=pt[2]*Math.PI/180;
   const px=pt[0]-Math.sin(a)*p.off,py=pt[1]+Math.cos(a)*p.off,edge=fade?clamp(Math.min(s,len-s)/(len*.06),0,1):1;
   setA(p.g,'transform','translate('+fmt(px)+' '+fmt(py)+') rotate('+fmt(pt[2])+')');setA(p.g,'opacity',fmt(edge));
  }
 }
 for(const c of n.children)update(c,t);
}
const colorAttrs=attrs=>{const a={};for(const k in attrs||{})a[k]=typeof attrs[k]==='string'?color(attrs[k]):attrs[k];return a;};
const helpers={clamp,lerp,ease,color,W,H,D,CONFIG,el:(tag,attrs,parent)=>mk(tag,colorAttrs(attrs),parent||customLayer)};
let art=null;
const api={D,W,H,svg,hud,tokens:TOKENS,clamp,lerp,ease,color,t:0,
 seg:(t,a,b,e)=>ease(e||'linear',b>a?(t-a)/(b-a):(t>=b?1:0)),
 mixColor:(a,b,p)=>{const x=parseColor(a),y=parseColor(b),q=clamp(p,0,1);return cssColor({c:x.map((v,i)=>v+(y[i]-v)*q)});},
 random:seed=>rand(Number(seed)||1),
 asset:id=>(SC.assets||{})[id],
 $:sel=>svg.querySelector(sel),$$:sel=>Array.from(svg.querySelectorAll(sel)),
 el:(tag,attrs,parent)=>mk(tag,colorAttrs(attrs),parent||art),
 set:(el,attrs)=>{if(!el)throw new Error('api.set: element not found');for(const k in attrs)setA(el,k,typeof attrs[k]==='string'?color(attrs[k]):(typeof attrs[k]==='number'?fmt(attrs[k]):attrs[k]));return el;},
 pointAt:(el,f)=>{if(!el)throw new Error('api.pointAt: path not found');const L=el.getTotalLength(),a=el.getPointAtLength(clamp(f,0,1)*L),b=el.getPointAtLength(clamp(f+.002,0,1)*L),c=el.getPointAtLength(clamp(f-.002,0,1)*L);return{x:a.x,y:a.y,angle:Math.atan2(b.y-c.y,b.x-c.x)*180/Math.PI,length:L};}};
function describe(e){const m=String(e&&e.message||e);return m;}
function fail(msg){
 if(!MC.broken){MC.broken=msg;root.dataset.error=msg;console.error('motioncards error: '+msg);}
 if(MC.port)MC.port.postMessage({type:'error',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid});
}
function renderAt(ms){
 const t=clamp(Number(ms)||0,0,D);
 if(MC.broken)return;
 try{
  const cx=camTrack.x?sample(camTrack.x,t):W/2,cy=camTrack.y?sample(camTrack.y,t):H/2,z=camTrack.zoom?sample(camTrack.zoom,t):1;
  setA(cam,'transform','translate('+fmt(W/2)+' '+fmt(H/2)+') scale('+fmt(z)+') translate('+fmt(-cx)+' '+fmt(-cy)+')');
  setA(customLayer,'transform',cam.getAttribute('transform'));
  for(const n of roots)update(n,t);
  if(CONFIG.has_custom&&typeof renderCustom==='function'){customLayer.replaceChildren();renderCustom(customLayer,t,helpers);}
  if(CONFIG.has_script){api.t=t;render(t,api);}
  root.dataset.ended=t>=D?'1':'0';root.dataset.t=String(t);
 }catch(e){fail((CONFIG.has_script?'render(t='+t+'): ':'')+describe(e));}
}
try{
 if(__MC_BOOT.errors.length){const x=__MC_BOOT.errors[0];throw new Error(x.m+(x.l>=AUTHOR_LINE?' (script line '+(x.l-AUTHOR_LINE+1)+')':''));}
 art=mk('g',{id:'art'},null);cam.insertBefore(art,cam.firstChild);
 if(SC.svg){
  const doc=new DOMParser().parseFromString(SC.svg,'image/svg+xml'),pe=doc.getElementsByTagName('parsererror')[0];
  if(pe)throw new Error('svg could not be parsed: '+pe.textContent.slice(0,200));
  for(const c of Array.from(doc.documentElement.childNodes))art.appendChild(document.importNode(c,true));
  for(const e of art.querySelectorAll('[href^="asset:"]'))e.setAttribute('href',(SC.assets||{})[e.getAttribute('href').slice(6)]||'');
  for(const e of art.querySelectorAll('*'))for(const k of ['fill','stroke','stop-color','flood-color','color']){const v=e.getAttribute(k);if(v&&v[0]==='@')e.setAttribute(k,color(v));}
 }
 for(const L of SC.layers||[])roots.push(build(L,L.fixed?hud:cam,1));
 if(SC.credits){const c=mk('text',{x:W-8,y:H-8,'text-anchor':'end','font-size':9,'font-family':FONTS.sans,fill:'#5f7a80',opacity:.8},hud);c.textContent=SC.credits.join(' · ');
  if(c.getComputedTextLength()>W-16)c.setAttribute('textLength',W-16),c.setAttribute('lengthAdjust','spacingAndGlyphs');}
 if(CONFIG.has_script&&typeof render!=='function')throw new Error('script must define function render(t, api)');
 if(CONFIG.has_custom&&typeof renderCustom!=='function')throw new Error('custom_renderer must define function renderCustom(layer, t, helpers)');
 if(CONFIG.has_script&&typeof setup==='function')setup(api);
}catch(e){fail(describe(e));}
function valid(m){return m&&m.protocol===1&&m.channel_id===CONFIG.channel_id&&m.qid===CONFIG.qid;}
addEventListener('message',ev=>{
 if(ev.source!==parent||!CONFIG.allowed_host_origins.includes(ev.origin))return;
 const m=ev.data;if(!m||m.type!=='connect'||!valid(m)||!ev.ports?.[0]||MC.port)return;
 MC.port=ev.ports[0];MC.port.onmessage=e=>{
   const x=e.data;if(!valid(x)||MC.destroyed)return;
   if(MC.broken){MC.port.postMessage({type:'error',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid});return;}
   if(x.type==='tick'||x.type==='seek'){renderAt(x.time_ms);if(!MC.broken)MC.port.postMessage({type:x.time_ms>=CONFIG.duration_ms?'ended':'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:clamp(Number(x.time_ms)||0,0,CONFIG.duration_ms)});}
   else if(x.type==='restart'){renderAt(0);MC.port.postMessage({type:'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:0});}
   else if(x.type==='play'||x.type==='pause'){MC.port.postMessage({type:'state',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,time_ms:Number(x.time_ms)||0,playing:x.type==='play'});}
   else if(x.type==='destroy'){MC.destroyed=true;MC.port.close();}
 };
 MC.port.start();
 if(MC.broken)MC.port.postMessage({type:'error',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid});
 else MC.port.postMessage({type:'ready',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid,duration_ms:CONFIG.duration_ms});
});
renderAt(0);
parent.postMessage({type:'kafu-motioncards-ready',protocol:1,channel_id:CONFIG.channel_id,qid:CONFIG.qid},'*');
})();
"""

BOOT_JS=("\"use strict\";var __MC_BOOT={config:__CFG__,errors:[]};"
 "addEventListener('error',function(e){__MC_BOOT.errors.push({m:String(e&&e.message||'script error'),l:Number(e&&e.lineno)||0});});"
 "(function(){var warned=false;function inert(){if(!warned){warned=true;console.warn('motioncards: timers and requestAnimationFrame are inert; animate inside render(t, api) so pause and seek work');}return 0;}"
 "['setTimeout','setInterval','requestAnimationFrame','requestIdleCallback'].forEach(function(k){self[k]=inert;});"
 "var a=0x2545F491;Math.random=function(){a=(a+0x6D2B79F5)>>>0;var t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};})();")

def compile_scene_v2(scene:dict,allowed:list[str],runtime_version:int)->str:
    s={k:scene[k] for k in ("stage","palette","gradients","assets","camera","layers","svg","credits") if k in scene}
    if "svg" in s:
        head=s["svg"].split(">",1)[0]
        if "xmlns=" not in head:s["svg"]=s["svg"].replace("<svg",'<svg xmlns="http://www.w3.org/2000/svg"',1)
    script=str(scene.get("script") or "").replace("\r\n","\n")
    custom=str(scene.get("custom_renderer") or "").replace("\r\n","\n")
    used={}
    text=json.dumps(s,ensure_ascii=False)+script+custom
    for name,val in BUILTIN_TOKENS.items():
        if "@"+name in text:used[name]=val
    cfg={"qid":str(scene["qid"]),"duration_ms":int(scene["duration_ms"]),"engine":2,"scene":s,"tokens":used,"has_script":bool(script),"has_custom":bool(custom),
         "channel_id":"","allowed_host_origins":allowed,"runtime_version":runtime_version}
    cfgtext=json.dumps(cfg,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    bg="#fbfaf7"
    stage=scene.get("stage") or {}
    if isinstance(stage.get("background"),str) and HEX_RE.fullmatch(stage["background"]):bg=stage["background"]
    head="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;height:100%;background:"""+bg+""";color:#16323a;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Sans Arabic",Arial,sans-serif;-webkit-font-smoothing:antialiased}#root{height:100%;overflow:hidden}svg{width:100%;height:100%;display:block;text-rendering:geometricPrecision;shape-rendering:geometricPrecision}</style></head>
<body><main id="root" data-engine="2"><svg id="stage" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Kafu MotionCards animation"></svg></main>
<script>"""+BOOT_JS.replace("__CFG__",cfgtext)+"""</script>
<script>
"""
    author_line=head.count("\n")+1
    author=(script+"\n"+custom).strip("\n")
    runtime=RUNTIME_V2_JS.replace("\r\n","\n").replace("__MC_AUTHOR_LINE__",str(author_line))
    return head+author+"""
</script>
<script>"""+runtime+"""</script></body></html>"""
