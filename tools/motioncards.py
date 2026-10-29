#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motioncards.lib.core import adapt_exports,resolve_answer
from motioncards.lib.package import scaffold_workspace
from motioncards.lib.multipart import build_package_set,validate_package_part
from motioncards.lib.compiler import compile_scene,validate_scene,preview_host_html
from motioncards.lib.engine_v2 import lint_scene_v2
from motioncards.lib.spec import parse_package_filename

def load(paths):return adapt_exports([json.loads(Path(x).read_text(encoding="utf-8")) for x in paths])

def overrides(values):
    out={}
    for item in values or []:
        qid,ms=item.split("=",1);out[qid]=int(ms)
    return out

def scene_targets(targets,workspace):
    paths=list(targets or [])
    if workspace:paths+=sorted((workspace/"scenes").glob("*.scene.json"))
    if not paths:raise SystemExit("give scene files or --workspace")
    out=[]
    for p in paths:
        try:out.append((p,json.loads(p.read_text(encoding="utf-8"))))
        except json.JSONDecodeError as exc:raise SystemExit(f"{p}: invalid JSON: {exc}")
    return out

def main():
    ap=argparse.ArgumentParser(prog="motioncards")
    sub=ap.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("scaffold")
    s.add_argument("exports",nargs="+")
    s.add_argument("--out",type=Path,required=True)
    s.add_argument("--package-id",required=True)
    s.add_argument("--revision",type=int,required=True)
    g=s.add_mutually_exclusive_group(required=True)
    g.add_argument("--qids",nargs="+")
    g.add_argument("--count",type=int)
    s.add_argument("--duration-ms",type=int)
    s.add_argument("--duration",action="append",default=[],help="QID=milliseconds")
    s.add_argument("--inspected-image-qid",action="append",default=[])
    s.add_argument("--replace",action="append",default=[],help="Selected QID to mark as an intended replacement; confirmation is still required before activation")
    s.add_argument("--schema",type=int,choices=[1,2],default=2,help="Starter scene schema (2 = current engine; 1 = legacy)")

    p=sub.add_parser("package")
    p.add_argument("exports",nargs="+")
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--no-voice",action="store_true",help="Package without voice-over (only for re-packaging old silent cards; new cards always get voice)")

    v=sub.add_parser("validate");v.add_argument("zip",type=Path)
    f=sub.add_parser("filename");f.add_argument("name")
    pr=sub.add_parser("preview");pr.add_argument("--workspace",type=Path,required=True);pr.add_argument("--port",type=int,default=8767)
    im=sub.add_parser("import-svg",help="Clean, fit and add an SVG illustration (file or URL) to a scene; the model only references it by id")
    im.add_argument("source",help="local .svg path, https URL, or lib:<name> from the bundled art library (see: library)");im.add_argument("--scene",type=Path,required=True)
    im.add_argument("--id",required=True);im.add_argument("--box",required=True,help="x,y,width,height in stage pixels")
    im.add_argument("--template",action="store_true",help="reusable symbol: --box is width,height centred on 0,0; draw copies with <use href=#id>")
    im.add_argument("--fit",default="contain",choices=["contain","cover","stretch"]);im.add_argument("--decimals",type=int,default=None,help="override the automatic precision (default: fewest decimals that stay under 0.05 stage px error)")
    im.add_argument("--credit",help='licence attribution shown on the card, e.g. "Heart: Servier Medical Art, CC BY 3.0"')
    lg=sub.add_parser("library-check",help="Gate a proposed library change: PASS only if it is purely additive and every addition proves itself")
    lg.add_argument("--base",default="origin/main");lg.add_argument("--report",type=Path);lg.add_argument("--no-render",action="store_true")
    sub.add_parser("library",help="List the bundled professional art (import with import-svg lib:<name>)")
    rc=sub.add_parser("recipes",help="Add the tested animation recipes (R.flow, R.bleed, R.impulses, R.lump, R.travel, R.callout, ...) to scenes' script");rc.add_argument("scenes",type=Path,nargs="+")
    sk=sub.add_parser("style-kit",help="Add the shading kit (kit-volume, kit-tissue, kit-nerve, ...) to scenes' svg");sk.add_argument("scenes",type=Path,nargs="+")
    li=sub.add_parser("lint",help="Validate scenes and print layout warnings")
    li.add_argument("targets",nargs="*",type=Path,help="scene .json files");li.add_argument("--workspace",type=Path)
    rn=sub.add_parser("render",help="Render scenes to PNG frames + contact sheet (needs playwright + Chromium)")
    rn.add_argument("targets",nargs="*",type=Path,help="scene .json files");rn.add_argument("--workspace",type=Path)
    rn.add_argument("--out",type=Path,default=Path("render"));rn.add_argument("--frames",type=int,default=6)
    rn.add_argument("--times",help="comma-separated milliseconds, e.g. 0,1500,4000")
    rn.add_argument("--sizes",default="phone,tablet",help="phone,tablet")

    ls=sub.add_parser("lesson",help="Build image lessons: lessons/<QID>.lesson.json -> scene + voice (run with the voice venv python)")
    ls.add_argument("--workspace",type=Path,required=True);ls.add_argument("--qids",nargs="*")

    a=ap.parse_args()
    if a.cmd=="lesson":
        from motioncards.lib.lesson import build_lesson
        qids=a.qids or sorted(p.name.split(".")[0] for p in (a.workspace/"lessons").glob("Q*.lesson.json"))
        if not qids:raise SystemExit(f"no lessons/Q*.lesson.json in {a.workspace}")
        for qid in qids:print(json.dumps(build_lesson(a.workspace,qid)))
        return
    if a.cmd=="scaffold":
        b=load(a.exports)
        result=scaffold_workspace(b,a.out,a.package_id.upper(),a.revision,a.qids,a.count,a.duration_ms,overrides(a.duration),set(a.inspected_image_qid),set(a.replace),a.schema)
        print(json.dumps(result,indent=2));return
    if a.cmd=="library-check":
        from motioncards.lib.library_gate import check
        try:rep=check(a.base,render=not a.no_render);md=rep.markdown()
        except Exception as exc:   # an unexpected error is never a pass
            rep=None;md=f"## MotionCards library gate: FAIL\n\n- ❌ gate crashed: {type(exc).__name__}: {exc}"
        print(md)
        if a.report:a.report.write_text(md+"\n",encoding="utf-8")
        sys.exit(1 if rep is None else (0 if rep.passed else (2 if not rep.fail else 1)))
    if a.cmd=="library":
        from motioncards.lib.assets import library_index
        idx=library_index()
        for name,item in idx["art"].items():print(f"lib:{name:22} {item['view']}  [use: {item['use']}]")
        print("credit added automatically: "+idx["credit"]);return
    if a.cmd=="recipes":
        from motioncards.lib.assets import add_recipes,add_style_kit
        for path in a.scenes:
            scene=json.loads(path.read_text(encoding="utf-8"))
            added=add_recipes(scene);add_style_kit(scene)   # recipes draw with the kit's fills and filters
            if scene.get("schema_version")==2:validate_scene(scene,str(scene.get("qid")),scene.get("duration_ms"))
            path.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"{path}: {'recipes added' if added else 'recipes already present'}")
        return
    if a.cmd=="style-kit":
        from motioncards.lib.assets import add_style_kit
        for path in a.scenes:
            scene=json.loads(path.read_text(encoding="utf-8"))
            added=add_style_kit(scene)
            if scene.get("schema_version")==2:validate_scene(scene,str(scene.get("qid")),scene.get("duration_ms"))
            path.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"{path}: {'kit added' if added else 'kit already present'}")
        return
    if a.cmd=="import-svg":
        from motioncards.lib.assets import prepare_svg,add_to_scene
        if a.source.startswith("lib:"):
            from motioncards.lib.assets import library_art
            text,lib_credit=library_art(a.source[4:])
            if not a.credit:a.credit=lib_credit
        elif a.source.startswith(("http://","https://")):
            import urllib.request
            with urllib.request.urlopen(a.source,timeout=30) as r:raw=r.read(5_000_001)
            if len(raw)>5_000_000:raise SystemExit("downloaded file is larger than 5 MB")
            text=raw.decode("utf-8")
        else:text=Path(a.source).read_text(encoding="utf-8")
        from motioncards.lib.assets import prepare_template
        box=tuple(float(x) for x in a.box.split(","))
        if len(box)!=(2 if a.template else 4):raise SystemExit("--box needs "+("width,height" if a.template else "x,y,width,height"))
        scene=json.loads(a.scene.read_text(encoding="utf-8"))
        frag=prepare_template(text,a.id,box[0],box[1],a.decimals) if a.template else prepare_svg(text,a.id,box,a.decimals,a.fit)
        add_to_scene(scene,frag,a.credit)
        if scene.get("schema_version")==2:validate_scene(scene,str(scene.get("qid")),scene.get("duration_ms"))
        a.scene.write_text(json.dumps(scene,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"imported":a.id,"source_bytes":len(text.encode()),"fragment_bytes":len(frag.encode()),"use_in_script":f"api.$('#{a.id}')","use_in_svg":f"<use href=\"#{a.id}\"/>"},indent=2));return
    if a.cmd in {"lint","render"}:
        scenes=scene_targets(a.targets,a.workspace)
        problems=0;report=[]
        for path,scene in scenes:
            try:
                validate_scene(scene,str(scene.get("qid")),scene.get("duration_ms"))
                warnings=lint_scene_v2(scene) if scene.get("schema_version")==2 else []
                report.append({"scene":str(path),"status":"PASS","warnings":warnings})
            except ValueError as exc:
                problems+=1;report.append({"scene":str(path),"status":"FAIL","error":str(exc)})
        if a.cmd=="lint" or problems:
            print(json.dumps(report,ensure_ascii=False,indent=2))
            if problems:sys.exit(1)
            return
        from motioncards.lib.render import render_scenes
        times=[int(x) for x in a.times.split(",")] if a.times else None
        out=render_scenes([sc for _,sc in scenes],a.out,times=times,frames=a.frames,sizes=[x.strip() for x in a.sizes.split(",") if x.strip()])
        for row,item in zip(report,out):row.update(item)
        print(json.dumps(report,ensure_ascii=False,indent=2));return
    if a.cmd=="package":
        for path,scene in scene_targets([],a.workspace):
            if scene.get("schema_version")==2:
                for w in lint_scene_v2(scene):print(f"warning: {path.name}: {w}",file=sys.stderr)
        b=load(a.exports);paths=build_package_set(b,a.workspace,a.out,require_voice=not a.no_voice)
        total=sum(len(validate_package_part(p)["animations"]) for p in paths)
        print(json.dumps({"zips":[str(p) for p in paths],"animations":total},indent=2));return
    if a.cmd=="validate":
        m=validate_package_part(a.zip)
        print(json.dumps({"status":"PASS","package_id":m["package_id"],"revision":m["package_revision"],"animations":len(m["animations"])},indent=2));return
    if a.cmd=="filename":
        print(json.dumps(parse_package_filename(a.name)));return
    if a.cmd=="preview":
        import http.server,socketserver
        selection=json.loads((a.workspace/"selection.json").read_text())
        raw=sorted((a.workspace/"input").glob("raw-export-*.json"))
        if not raw:raise ValueError("preview_source_export_missing")
        bundle=load(raw);by_id={q["id"]:q for q in bundle.questions}
        out=a.workspace/"preview";out.mkdir(exist_ok=True)
        links=[];origin=f"http://127.0.0.1:{a.port}"
        for row in selection["selected"]:
            qid=row["qid"];scene=json.loads((a.workspace/"scenes"/f"{qid}.scene.json").read_text())
            validate_scene(scene,qid,int(row["duration_ms"]))
            question=by_id.get(qid)
            if not question:raise ValueError("preview_question_missing:"+qid)
            answers=resolve_answer(question)["statements"]
            (out/f"{qid}.html").write_text(compile_scene(scene,[origin],preview=True),encoding="utf-8")
            host_name=f"{qid}-preview.html"
            (out/host_name).write_text(preview_host_html(scene,answers,a.port),encoding="utf-8")
            links.append(f'<li><a href="/{host_name}">{qid}</a> — {row["duration_ms"]} ms</li>')
        (out/"index.html").write_text("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Kafu MotionCards preview</title><h1>Kafu MotionCards preview</h1><p>Each link opens the trusted preview host with the real MessageChannel/timeline contract.</p><ul>"+"".join(links)+"</ul>",encoding="utf-8")
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(out),**kwargs)
            def log_message(self,fmt,*args):pass
        print(f"Preview: {origin}/",flush=True)
        with socketserver.TCPServer(("127.0.0.1",a.port),Handler) as server:server.serve_forever()
        return
if __name__=="__main__":main()
