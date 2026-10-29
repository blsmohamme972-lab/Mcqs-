"""Library gate: decides whether a proposed library change is safe to merge without a human.

A change passes only if it is purely additive and every addition proves itself:
  * it touches nothing outside motioncards/library/ (art/*.svg added, library.json, recipes.js, demos/*.js added);
  * existing library entries, existing recipes and the style kit are byte-for-byte unchanged;
  * each new drawing has a safe licence, a source, a reason and the card(s) it was used in, imports
    cleanly, stays under the size cap, renders without errors and is not a near-copy of existing art;
  * each new recipe ships a demo that uses it, and the demo validates, lints clean and renders on
    phone and tablet with deterministic seeking.
Anything else is reported as "needs a human" and must not be auto-merged.
"""
from __future__ import annotations
import io,json,re,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIB="motioncards/library/"
ALLOWED_LICENCES={"CC0","Public domain","CC BY 3.0","CC BY 4.0","MIT"}
ALLOWED_STYLES={"servier","togo","other"}
MAX_NEW_ART=6
MAX_NEW_RECIPES=3
MAX_ART_FRAGMENT_BYTES=150_000
MAX_RECIPES_BYTES=40_000
DUPLICATE_MEAN_DIFF=6.0          # 0-255 grey levels at 128x128; below this the drawing is a near-copy
QID_RE=re.compile(r"Q\d{9}")

class Report:
    def __init__(self):self.fail=[];self.ok=[];self.human=[]
    def bad(self,msg):self.fail.append(msg)
    def good(self,msg):self.ok.append(msg)
    def needs_human(self,msg):self.human.append(msg)
    @property
    def passed(self):return not self.fail and not self.human
    def markdown(self)->str:
        head="PASS: safe to merge automatically" if self.passed else ("NEEDS A HUMAN" if not self.fail else "FAIL")
        lines=[f"## MotionCards library gate: {head}",""]
        for title,rows,mark in (("Blocking problems",self.fail,"❌"),("Needs human review",self.human,"🟡"),("Checks passed",self.ok,"✅")):
            if rows:lines+= [f"**{title}**",""]+[f"- {mark} {r}" for r in rows]+[""]
        return "\n".join(lines)

def _git(root:Path,*args)->str:
    return subprocess.run(["git",*args],cwd=root,check=True,capture_output=True,text=True).stdout

def _base_text(root:Path,base:str,path:str)->str|None:
    try:return _git(root,"show",f"{base}:{path}")
    except subprocess.CalledProcessError:return None

def _recipe_members(src:str)->dict[str,str]:
    """Top-level members of `const R = {...}`, keyed by name, with their exact source text."""
    body=src.split("const R = {",1)[1].rsplit("};",1)[0]
    starts=[(m.start(),m.group(1)) for m in re.finditer(r"^  ([A-Za-z_]\w*)\s*[(:]",body,re.M)]
    out={}
    for i,(pos,name) in enumerate(starts):
        end=starts[i+1][0] if i+1<len(starts) else len(body)
        lines=body[pos:end].rstrip().split("\n")
        while len(lines)>1 and (not lines[-1].strip() or lines[-1].lstrip().startswith("//")):lines.pop()   # comments above the next member are not part of this one
        out[name]="\n".join(lines).rstrip()
    return out

def _render_png(fragment:str,page)->"Image":
    from PIL import Image
    page.set_content(f'<body style="margin:0;background:#fff"><svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">{fragment}</svg></body>')
    return Image.open(io.BytesIO(page.screenshot(clip={"x":0,"y":0,"width":128,"height":128}))).convert("L")

def _mean_diff(a,b)->float:
    from PIL import ImageChops
    h=ImageChops.difference(a,b).histogram();return sum(i*n for i,n in enumerate(h))/sum(h)

def check(base:str="origin/main",render:bool=True,root:Path=ROOT)->Report:
    from motioncards.lib.assets import prepare_svg,add_to_scene,add_style_kit,check_credit,AssetImportError
    root=Path(root);LIBRARY_DIR=root/LIB
    from motioncards.lib.compiler import validate_scene
    from motioncards.lib.engine_v2 import lint_scene_v2
    rep=Report()
    fork=_git(root,"merge-base",base,"HEAD").strip()        # compare with where the branch left base, including uncommitted work
    changes=[l.split("\t") for l in _git(root,"diff","--name-status","--no-renames",fork).splitlines() if l.strip()]
    changes+=[["A",p] for p in _git(root,"ls-files","--others","--exclude-standard").splitlines() if p.startswith(LIB)]
    if not changes:rep.bad("no changes against "+base);return rep
    added_art,added_demos=[],[]
    for status,path in ((c[0],c[-1]) for c in changes):
        if not path.startswith(LIB):rep.needs_human(f"changes a file outside the library: {path}");continue
        rel=path[len(LIB):]
        if re.fullmatch(r"art/[a-z0-9][a-z0-9_.-]*\.svg",rel) and status=="A":added_art.append(rel)
        elif re.fullmatch(r"demos/[A-Za-z_]\w*\.js",rel) and status=="A":added_demos.append(rel)
        elif rel in {"library.json","recipes.js"} and status=="M":pass
        else:rep.needs_human(f"{status} {path}: only adding art/demos or extending library.json/recipes.js can merge automatically")
    # --- library.json: purely additive, every new entry fully documented ---
    head_idx=json.loads((LIBRARY_DIR/"library.json").read_text(encoding="utf-8"))
    base_idx=json.loads(_base_text(root,fork,LIB+"library.json") or "{}")
    for k in set(base_idx)-{"art"}:
        if base_idx[k]!=head_idx.get(k):rep.needs_human(f"library.json: top-level '{k}' changed")
    base_art,head_art=base_idx.get("art",{}),head_idx.get("art",{})
    for name,item in base_art.items():
        if head_art.get(name)!=item:rep.needs_human(f"library.json: existing entry '{name}' changed or removed")
    new=[n for n in head_art if n not in base_art]
    if len(new)>MAX_NEW_ART:rep.bad(f"{len(new)} new drawings in one change (max {MAX_NEW_ART}); split it")
    files_claimed=set()
    for name in new:
        item=head_art[name];where=f"library.json '{name}'"
        missing=[f for f in ("file","view","use","license","source","reason","used_in") if not item.get(f)]
        if missing:rep.bad(f"{where}: missing {', '.join(missing)}");continue
        if item["license"] not in ALLOWED_LICENCES:rep.bad(f"{where}: licence '{item['license']}' not in {sorted(ALLOWED_LICENCES)}")
        if item.get("style","other") not in ALLOWED_STYLES:rep.bad(f"{where}: style must be one of {sorted(ALLOWED_STYLES)}")
        if not str(item["source"]).startswith("https://"):rep.bad(f"{where}: source must be an https URL to the original file")
        if len(str(item["reason"]).strip())<20:rep.bad(f"{where}: reason must say why this is an improvement (20+ characters)")
        if not isinstance(item["used_in"],list) or not all(QID_RE.fullmatch(str(q)) for q in item["used_in"]):rep.bad(f"{where}: used_in must list the card QIDs that use it")
        credit=item.get("credit") or head_idx.get("credit","")
        try:check_credit(credit)
        except AssetImportError as e:rep.bad(f"{where}: {e}")
        if item["license"].startswith("CC BY") and item["license"] not in credit:rep.bad(f"{where}: credit must name the licence '{item['license']}'")
        if item["file"] not in added_art:rep.bad(f"{where}: file {item['file']} is not a newly added art/*.svg")
        files_claimed.add(item["file"])
    for f in added_art:
        if f not in files_claimed:rep.bad(f"{f}: added but no new library.json entry uses it")
    # --- art quality: imports, size, validates, renders, not a duplicate ---
    page=browser=pw=None
    if render and new:
        from playwright.sync_api import sync_playwright
        from motioncards.lib.render import _launch
        pw=sync_playwright().start();browser=_launch(pw);page=browser.new_page(viewport={"width":128,"height":128})
    try:
        existing_imgs={}
        for name in new:
            item=head_art[name]
            if item.get("file") not in files_claimed or not (LIBRARY_DIR/item["file"]).is_file():continue
            text=(LIBRARY_DIR/item["file"]).read_text(encoding="utf-8")
            try:frag=prepare_svg(text,"art",(0,0,440,440))
            except AssetImportError as e:rep.bad(f"'{name}': does not import: {e}");continue
            if len(frag.encode())>MAX_ART_FRAGMENT_BYTES:rep.bad(f"'{name}': {len(frag.encode())//1024} KB after import (max {MAX_ART_FRAGMENT_BYTES//1024} KB); pick a lighter drawing")
            scene={"schema_version":2,"qid":"Q000000001","duration_ms":3000,"takeaway":"Library gate.","script":"function render(t,api){}"}
            try:add_to_scene(scene,frag,item.get("credit") or head_idx.get("credit"));validate_scene(scene,"Q000000001",3000)
            except AssetImportError:continue                                   # licence already reported above
            except ValueError as e:rep.bad(f"'{name}': scene invalid: {e}");continue
            if lint_scene_v2(scene):rep.bad(f"'{name}': lint warnings {lint_scene_v2(scene)}")
            if page is None:continue
            img=_render_png(prepare_svg(text,"a",(0,0,128,128)),page)
            if img.getextrema()[0]>=250:rep.bad(f"'{name}': renders blank");continue
            for other,oitem in head_art.items():
                if other==name:continue
                if other not in existing_imgs:
                    try:existing_imgs[other]=_render_png(prepare_svg((LIBRARY_DIR/oitem["file"]).read_text(encoding="utf-8"),"a",(0,0,128,128)),page)
                    except Exception:existing_imgs[other]=None
                o=existing_imgs[other]
                if o is not None and _mean_diff(img,o)<DUPLICATE_MEAN_DIFF:rep.bad(f"'{name}': near-duplicate of existing '{other}'")
            rep.good(f"drawing '{name}' ({item['license']}, {len(frag.encode())//1024} KB): imports, validates, renders, not a duplicate")
    finally:
        if browser:browser.close()
        if pw:pw.stop()
    # --- recipes: existing members untouched; each new member demonstrated ---
    head_rec=(LIBRARY_DIR/"recipes.js").read_text(encoding="utf-8");base_rec=_base_text(root,fork,LIB+"recipes.js") or head_rec
    if len(head_rec.encode())>MAX_RECIPES_BYTES:rep.bad(f"recipes.js is {len(head_rec.encode())} bytes (max {MAX_RECIPES_BYTES}); every card carries it")
    try:bm,hm=_recipe_members(base_rec),_recipe_members(head_rec)
    except IndexError:rep.bad("recipes.js no longer defines `const R = {...}`");bm,hm={},{}
    for name,src in bm.items():
        if hm.get(name)!=src:rep.needs_human(f"recipes.js: existing recipe '{name}' changed or removed")
    new_rec=[n for n in hm if n not in bm]
    if len(new_rec)>MAX_NEW_RECIPES:rep.bad(f"{len(new_rec)} new recipes in one change (max {MAX_NEW_RECIPES})")
    demos=[]
    for name in new_rec:
        demo=f"demos/{name}.js"
        if demo not in added_demos and not (LIBRARY_DIR/demo).is_file():rep.bad(f"recipe '{name}': add {LIB}{demo} showing it in a scene");continue
        code=(LIBRARY_DIR/demo).read_text(encoding="utf-8")
        if f"R.{name}(" not in code:rep.bad(f"{demo}: does not call R.{name}(...)");continue
        scene={"schema_version":2,"qid":"Q000000002","duration_ms":3000,"takeaway":"Recipe demo.","script":code}
        scene["script"]=head_rec.rstrip("\n")+"\n"+code;add_style_kit(scene)   # the proposed recipes, not the installed ones
        try:validate_scene(scene,"Q000000002",3000)
        except ValueError as e:rep.bad(f"{demo}: scene invalid: {e}");continue
        if lint_scene_v2(scene):rep.bad(f"{demo}: lint warnings {lint_scene_v2(scene)}");continue
        demos.append((name,scene))
    for d in added_demos:
        if d[len("demos/"):-3] not in new_rec:rep.bad(f"{d}: demo for a recipe that is not new")
    if render and demos:
        from motioncards.lib.render import render_scenes
        with tempfile.TemporaryDirectory() as td:
            for name,scene in demos:
                try:render_scenes([scene],Path(td),frames=5,sizes=["phone","tablet"],sheet=False);rep.good(f"recipe '{name}': demo renders on phone and tablet with deterministic seeking")
                except Exception as e:rep.bad(f"recipe '{name}': demo failed in the browser: {e}")
    if not new and not new_rec and not rep.fail and not rep.human:rep.bad("nothing new was added")
    return rep
