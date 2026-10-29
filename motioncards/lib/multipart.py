from __future__ import annotations
import json,shutil,tempfile,zipfile
from pathlib import Path
from .compiler import compile_scene
from . import package as package_module
from .package import build_package,validate_package,check_archive_structure,sha256_bytes
from .spec import MANIFEST_NAME

TARGET_UNCOMPRESSED=8*1024*1024

def _target_uncompressed():
    return min(TARGET_UNCOMPRESSED,max(1024,package_module.MAX_ZIP_BYTES//2))

def _rewrite_manifest(path:Path,update:dict):
    with zipfile.ZipFile(path) as src:
        files={info.filename:src.read(info.filename) for info in src.infolist()}
    manifest=json.loads(files[MANIFEST_NAME]);manifest.update(update)
    files[MANIFEST_NAME]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name,data in sorted(files.items()):
            zi=zipfile.ZipInfo(name);zi.date_time=(2026,1,1,0,0,0);zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16
            out.writestr(zi,data)
    check_archive_structure(path)

def validate_package_part(path:Path):
    manifest=validate_package(path)
    mp=manifest.get("multipart")
    if mp is None:return manifest
    if not isinstance(mp,dict):raise ValueError("multipart_invalid")
    part_index=mp.get("part_index");total=mp.get("total_parts");batch=mp.get("batch_qids");part=mp.get("part_qids")
    if not isinstance(part_index,int) or not isinstance(total,int) or not 1<=part_index<=total<=100:raise ValueError("multipart_identity_invalid")
    if not isinstance(batch,list) or not batch or len(batch)!=len(set(batch)):raise ValueError("multipart_batch_invalid")
    qids=[row["qid"] for row in manifest["animations"]]
    if part!=qids or manifest.get("selection",{}).get("qids")!=qids:raise ValueError("multipart_part_membership_invalid")
    if any(qid not in batch for qid in qids):raise ValueError("multipart_qid_outside_batch")
    if int(mp.get("batch_count",-1))!=len(batch):raise ValueError("multipart_batch_count_invalid")
    return manifest

def _estimate(bundle,workspace:Path,row:dict):
    qid=row["qid"];scene_path=workspace/"scenes"/f"{qid}.scene.json"
    scene=json.loads(scene_path.read_text(encoding="utf-8"))
    question=next(q for q in bundle.questions if q["id"]==qid)
    source={"question":question,"integrity":bundle.integrity[qid],"provenance":bundle.provenance}
    voice=workspace/"voice"/f"{qid}.opus"
    voice_bytes=voice.stat().st_size*7//3 if voice.exists() else 0   # the file itself plus its base64 copy inside the entry
    return len(compile_scene(scene).encode())+len(scene_path.read_bytes())+len(json.dumps(source,ensure_ascii=False).encode())+voice_bytes+8192

def build_package_set(bundle,workspace:Path,out_zip:Path,require_voice:bool=False):
    try:
        build_package(bundle,workspace,out_zip,require_voice)
        return [out_zip]
    except ValueError as exc:
        if str(exc)!="zip_too_large":raise
        out_zip.unlink(missing_ok=True)
    selection=json.loads((workspace/"selection.json").read_text(encoding="utf-8"))
    rows=selection["selected"];batch_qids=[row["qid"] for row in rows]
    chunks=[];current=[];weight=0
    for row in rows:
        w=_estimate(bundle,workspace,row)
        if current and weight+w>_target_uncompressed():
            chunks.append(current);current=[];weight=0
        current.append(row);weight+=w
    if current:chunks.append(current)
    if len(chunks)<2:raise ValueError("motioncards_single_animation_exceeds_zip_limit")
    outputs=[];total=len(chunks)
    for index,chunk in enumerate(chunks,1):
        with tempfile.TemporaryDirectory(prefix="motioncards-part-") as td:
            tmp=Path(td);(tmp/"scenes").mkdir()
            subset={**selection,"selected":chunk}
            (tmp/"selection.json").write_text(json.dumps(subset,ensure_ascii=False,indent=2)+"\n")
            for row in chunk:
                shutil.copy2(workspace/"scenes"/f"{row['qid']}.scene.json",tmp/"scenes"/f"{row['qid']}.scene.json")
                for ext in (".opus",".track.json"):
                    src=workspace/"voice"/f"{row['qid']}{ext}"
                    if src.exists():(tmp/"voice").mkdir(exist_ok=True);shutil.copy2(src,tmp/"voice"/src.name)
            name=out_zip.with_name(out_zip.stem+f"_part{index}of{total}.zip")
            build_package(bundle,tmp,name,require_voice)
            _rewrite_manifest(name,{"multipart":{"part_index":index,"total_parts":total,"batch_count":len(batch_qids),"batch_qids":batch_qids,"part_qids":[x["qid"] for x in chunk]}})
            validate_package_part(name);outputs.append(name)
    return outputs

def combine_parts(paths:list[Path]):
    if not paths:raise ValueError("motioncards_parts_missing")
    manifests=[validate_package_part(p) for p in paths]
    if len(paths)==1 and manifests[0].get("multipart") is None:
        return manifests[0],{row["qid"]:paths[0] for row in manifests[0]["animations"]},sha256_bytes(paths[0].read_bytes())
    if any(m.get("multipart") is None for m in manifests):raise ValueError("multipart_contract_missing")
    first=manifests[0];identity=(first["package_id"],first["package_revision"],first["runtime_version"],first["protocol_version"],first.get("source"))
    for m in manifests[1:]:
        if (m["package_id"],m["package_revision"],m["runtime_version"],m["protocol_version"],m.get("source"))!=identity:raise ValueError("multipart_identity_conflict")
    total=first["multipart"]["total_parts"];batch=first["multipart"]["batch_qids"]
    by_index={}
    for path,m in zip(paths,manifests):
        mp=m["multipart"]
        if mp["total_parts"]!=total or mp["batch_qids"]!=batch:raise ValueError("multipart_batch_conflict")
        if mp["part_index"] in by_index:raise ValueError("multipart_duplicate_part")
        by_index[mp["part_index"]]=(path,m)
    if set(by_index)!=set(range(1,total+1)):raise ValueError("multipart_incomplete")
    row_by_qid={};source_by_qid={}
    for idx in range(1,total+1):
        path,m=by_index[idx]
        for row in m["animations"]:
            qid=row["qid"]
            if qid in row_by_qid:raise ValueError("multipart_duplicate_qid")
            row_by_qid[qid]=row;source_by_qid[qid]=path
    if set(row_by_qid)!=set(batch):raise ValueError("multipart_batch_membership_incomplete")
    combined={**first,"multipart":None,"animations":[row_by_qid[qid] for qid in batch],
              "selection":{**first["selection"],"qids":batch,"count":len(batch)}}
    digest_input="".join(sha256_bytes(by_index[i][0].read_bytes()) for i in range(1,total+1)).encode()
    return combined,source_by_qid,sha256_bytes(digest_input)
