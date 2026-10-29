from __future__ import annotations
import hashlib,json,posixpath,re,stat,unicodedata,zipfile
from urllib.parse import urlsplit
from pathlib import Path
from .core import AdaptedExport,select_questions,resolve_answer,content_hash
from .compiler import compile_scene,validate_scene
from .voice import validate_voice
from .spec import *

def sha256_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def safe_path(name:str)->str:
    raw=str(name).replace("\\","/")
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:",raw):raise ValueError("zip_path_absolute")
    parts=raw.split("/")
    if any(x in {"","..","."} for x in parts):raise ValueError("zip_path_traversal")
    norm=posixpath.normpath(raw)
    if norm.startswith("../") or norm!=raw:raise ValueError("zip_path_noncanonical")
    return norm

def check_archive_structure(path:Path):
    if path.stat().st_size>MAX_ZIP_BYTES:raise ValueError("zip_too_large")
    seen=set();expanded=0
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>MAX_ENTRIES:raise ValueError("zip_too_many_entries")
        for info in infos:
            name=safe_path(info.filename)
            key=unicodedata.normalize("NFC",name).casefold()
            if key in seen:raise ValueError("zip_path_collision")
            seen.add(key)
            mode=(info.external_attr>>16)&0o170000
            if mode==stat.S_IFLNK:raise ValueError("zip_symlink_rejected")
            if info.flag_bits&1:raise ValueError("zip_encrypted_rejected")
            if info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}:raise ValueError("zip_compression_unsupported")
            expanded+=info.file_size
            if expanded>MAX_EXPANDED_BYTES:raise ValueError("zip_expanded_too_large")
            if info.compress_size and info.file_size/info.compress_size>MAX_RATIO:raise ValueError("zip_member_ratio_exceeded")
            base=posixpath.basename(name).casefold();ext=Path(base).suffix.casefold()
            if base in {x.casefold() for x in FORBIDDEN_BASENAMES} or ext in FORBIDDEN_EXTENSIONS:raise ValueError("zip_executable_or_hosting_file_rejected")
            if "/" not in name and name not in ALLOWED_ROOT_FILES:raise ValueError("zip_root_file_unapproved")
            if "/" in name and not name.startswith(PUBLIC_PREFIXES+SOURCE_PREFIXES):raise ValueError("zip_prefix_unapproved")
        bad=z.testzip()
        if bad:raise ValueError("zip_crc_failed:"+bad)

def _starter_scene_v2(qid:str,ms:int,stem:str)->dict:
    title=" ".join(stem.split())
    if len(title)>90:title=title[:90].rsplit(" ",1)[0]+"…"
    return {"schema_version":2,"qid":qid,"duration_ms":ms,"takeaway":"EDIT: one short teaching takeaway",
        "stage":{"width":640,"height":560},
        "layers":[
            {"type":"text","text":title or "Key relationship","x":320,"y":64,"size":26,"weight":800,"max_width":580,"fit":True,"max_lines":2,"fixed":True},
            {"type":"circle","cx":180,"cy":300,"r":70,"fill":"@surface","stroke":"@ink","stroke_width":3},
            {"type":"circle","cx":460,"cy":300,"r":70,"fill":"@surface","stroke":"@ink","stroke_width":3,"show":[int(ms*.15),ms],"enter":"pop"},
            {"type":"arrow","x1":265,"y1":300,"x2":375,"y2":300,"stroke":"@accent","stroke_width":8,"show":[int(ms*.3),ms],"enter":"draw"}
        ]}

def scaffold_workspace(bundle:AdaptedExport,out:Path,package_id:str,revision:int,qids:list[str]|None,count:int|None,duration_ms:int|None,overrides:dict[str,int]|None=None,inspected_images:set[str]|None=None,replacement_qids:set[str]|None=None,schema:int=2):
    if schema not in {1,2}:raise ValueError("scene_schema_unsupported")
    if not PACKAGE_ID_RE.fullmatch(package_id):raise ValueError("package_id_invalid")
    if not isinstance(revision,int) or revision<1:raise ValueError("package_revision_invalid")
    selected=select_questions(bundle,qids,count,duration_ms,overrides,inspected_images)
    replacement_qids=set(replacement_qids or set());selected_ids={x["qid"] for x in selected}
    if not replacement_qids.issubset(selected_ids):raise ValueError("replacement_qid_not_selected")
    out.mkdir(parents=True,exist_ok=True);(out/"scenes").mkdir(exist_ok=True);(out/"input").mkdir(exist_ok=True)
    for i,e in enumerate(bundle.envelopes,1):
        (out/"input"/f"raw-export-{i:03d}.json").write_text(json.dumps(e,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    selection={"package_id":package_id,"package_revision":revision,"source":bundle.provenance,"scope":bundle.effective_scope,"warnings":bundle.warnings,"selected":[{"qid":x["qid"],"duration_ms":x["duration_ms"],"content_hash":x["integrity"]["content_hash"]} for x in selected]}
    (out/"selection.json").write_text(json.dumps(selection,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for item in selected:
        q=item["question"];ms=item["duration_ms"]
        if schema==2:scene=_starter_scene_v2(item["qid"],ms,str(q.get("stem") or ""))
        else:scene={"schema_version":1,"qid":item["qid"],"duration_ms":ms,"takeaway":"EDIT: one short teaching takeaway","layers":[
            {"type":"label","text":str(q.get("stem") or "")[:80],"x":320,"y":70,"size":24,"start_ms":0,"end_ms":ms,"from":{"opacity":0.2,"scale":0.96},"to":{"opacity":1,"scale":1}},
            {"type":"arrow","x1":190,"y1":230,"x2":450,"y2":230,"stroke":"#16606A","stroke_width":7,"start_ms":int(ms*.2),"end_ms":int(ms*.8),"from":{"opacity":0},"to":{"opacity":1}}
        ]}
        if item["qid"] in replacement_qids:scene["replace"]=True
        (out/"scenes"/f"{item['qid']}.scene.json").write_text(json.dumps(scene,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return selection

def workspace_voice(workspace:Path,qid:str):
    """The card's voice from voiceover/voiceover.py (work/<batch>/voice/<QID>.opus + .track.json), or None."""
    audio=workspace/"voice"/f"{qid}.opus";track=workspace/"voice"/f"{qid}.track.json"
    if not audio.exists() and not track.exists():return None
    if not (audio.exists() and track.exists()):raise ValueError("voice_incomplete:"+qid)
    return audio.read_bytes(),json.loads(track.read_text(encoding="utf-8"))

def build_package(bundle:AdaptedExport,workspace:Path,out_zip:Path,require_voice:bool=False):
    selection=json.loads((workspace/"selection.json").read_text(encoding="utf-8"))
    selected_ids=[x["qid"] for x in selection["selected"]];by_id={q["id"]:q for q in bundle.questions}
    records=[];files={}
    for sel in selection["selected"]:
        qid=sel["qid"];q=by_id.get(qid)
        if not q:raise ValueError("selected_question_missing:"+qid)
        integ=bundle.integrity[qid]
        if integ["content_hash"]!=sel["content_hash"]:raise ValueError("selection_hash_changed:"+qid)
        scene=json.loads((workspace/"scenes"/f"{qid}.scene.json").read_text(encoding="utf-8"))
        validate_scene(scene,qid,int(sel["duration_ms"]))
        voice=workspace_voice(workspace,qid)
        if voice is None and require_voice:raise ValueError("voice_missing:"+qid+" (run voiceover/voiceover.py make, or package with --no-voice)")
        voice_block=validate_voice(voice[0],voice[1],int(sel["duration_ms"])) if voice else None
        entry=compile_scene(scene,voice=voice[0] if voice else None)
        entry_path=f"entries/{qid}.html";scene_path=f"scenes/{qid}.scene.json";source_path=f"source/questions/{qid}.json"
        if voice:voice_block={"path":f"voice/{qid}.opus",**voice_block};files[voice_block["path"]]=voice[0]
        source_obj={"question":q,"integrity":integ,"provenance":bundle.provenance}
        source_bytes=(json.dumps(source_obj,ensure_ascii=False,indent=2)+"\n").encode()
        scene_bytes=(json.dumps(scene,ensure_ascii=False,indent=2)+"\n").encode();entry_bytes=entry.encode()
        if len(entry_bytes)>MAX_ENTRY_BYTES:raise ValueError("compiled_entry_too_large:"+qid)
        files[entry_path]=entry_bytes;files[scene_path]=scene_bytes;files[source_path]=source_bytes
        answer=resolve_answer(q)
        records.append({
            "book_id":q["book_id"],"book_version":q["version"],"chapter_id":q["chapter_id"],"qid":qid,
            "publisher_fingerprint":integ["publisher_fingerprint"],"publisher_fingerprint_source":integ.get("publisher_fingerprint_source"),
            "content_hash":integ["content_hash"],"content_hash_algorithm":"SHA-256","content_hash_canonicalization":"kafu-question-canonical-json-v1",
            "duration_ms":int(sel["duration_ms"]),"entry_path":entry_path,"entry_sha256":sha256_bytes(entry_bytes),
            "scene_path":scene_path,"scene_sha256":sha256_bytes(scene_bytes),"source_record_path":source_path,"source_record_sha256":sha256_bytes(source_bytes),
            "final_panel":{"takeaway":scene["takeaway"],"correct_answer_kind":answer["kind"],"correct_answer_statements":answer["statements"]},
            "replace":bool(scene.get("replace",False))
        })
        if voice_block:records[-1]["voice"]=voice_block
    manifest={
        "package_type":PACKAGE_TYPE,"schema_version":SCHEMA_VERSION,"package_id":selection["package_id"],"package_revision":selection["package_revision"],
        "runtime_version":RUNTIME_VERSION,"protocol_version":PROTOCOL_VERSION,"source":bundle.provenance,
        "selection":{"qids":selected_ids,"count":len(selected_ids),"scope":bundle.effective_scope,"warnings":bundle.warnings},
        "animations":records
    }
    files[MANIFEST_NAME]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    files["validation-report.json"]=(json.dumps({"status":"PASS","animations":len(records),"blocked":[],"package_type":PACKAGE_TYPE},indent=2)+"\n").encode()
    out_zip.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out_zip,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            zi=zipfile.ZipInfo(name);zi.date_time=(2026,1,1,0,0,0);zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16
            z.writestr(zi,data)
    check_archive_structure(out_zip)
    return manifest

def _validate_source_provenance(source:dict):
    if not isinstance(source,dict) or source.get("kind")!="published":raise ValueError("source_provenance_invalid")
    for field in ["catalog_url","index_url"]:
        raw=source.get(field)
        if raw in {None,""} and field=="index_url":continue
        u=urlsplit(str(raw or ""))
        if u.scheme!="https" or u.netloc!="kafu-content-1.blsmohamme97.workers.dev" or u.username or u.password or u.query or u.fragment:
            raise ValueError("source_provenance_url_invalid:"+field)
    for field in ["catalog_sha256","index_sha256"]:
        raw=source.get(field)
        if raw in {None,""} and field=="index_sha256":continue
        if not re.fullmatch(r"[a-f0-9]{64}",str(raw or ""),re.I):raise ValueError("source_provenance_hash_invalid:"+field)

def _validate_manifest_record(row:dict):
    required=["book_id","book_version","chapter_id","qid","publisher_fingerprint","content_hash","content_hash_algorithm",
              "content_hash_canonicalization","duration_ms","entry_path","entry_sha256","scene_path","scene_sha256",
              "source_record_path","source_record_sha256","final_panel","replace"]
    if not isinstance(row,dict) or any(k not in row for k in required):raise ValueError("manifest_animation_record_invalid")
    qid=str(row.get("qid") or "")
    if not QID_RE.fullmatch(qid):raise ValueError("manifest_qid_invalid")
    if not isinstance(row.get("book_id"),str) or not row["book_id"] or not isinstance(row.get("book_version"),int) or row["book_version"]<1:
        raise ValueError("manifest_book_identity_invalid")
    if not isinstance(row.get("chapter_id"),(str,int)) or isinstance(row.get("chapter_id"),bool):raise ValueError("manifest_chapter_identity_invalid")
    if row.get("content_hash_algorithm")!="SHA-256" or row.get("content_hash_canonicalization")!="kafu-question-canonical-json-v1":
        raise ValueError("manifest_content_hash_contract_invalid")
    if not re.fullmatch(r"[a-f0-9]{64}",str(row.get("publisher_fingerprint") or ""),re.I):raise ValueError("manifest_fingerprint_invalid")
    if not re.fullmatch(r"[a-f0-9]{64}",str(row.get("content_hash") or ""),re.I):raise ValueError("manifest_content_hash_invalid")
    if not isinstance(row.get("replace"),bool):raise ValueError("replace_intent_must_be_boolean")
    validate_duration(row.get("duration_ms"))
    panel=row.get("final_panel")
    if not isinstance(panel,dict) or not isinstance(panel.get("takeaway"),str) or not panel["takeaway"].strip():
        raise ValueError("final_panel_invalid")
    statements=panel.get("correct_answer_statements")
    if not isinstance(statements,list) or not statements or any(not isinstance(x,str) or not x.strip() for x in statements):
        raise ValueError("final_panel_answers_invalid")
    return qid

def validate_package(path:Path):
    check_archive_structure(path)
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        if MANIFEST_NAME not in names:raise ValueError("manifest_missing")
        try:m=json.loads(z.read(MANIFEST_NAME))
        except Exception as exc:raise ValueError("manifest_json_invalid") from exc
        if not isinstance(m,dict) or m.get("package_type")!=PACKAGE_TYPE or m.get("schema_version")!=SCHEMA_VERSION:raise ValueError("manifest_type_invalid")
        if not PACKAGE_ID_RE.fullmatch(str(m.get("package_id") or "")) or not isinstance(m.get("package_revision"),int) or isinstance(m.get("package_revision"),bool) or m["package_revision"]<1:raise ValueError("manifest_identity_invalid")
        if m.get("runtime_version")!=RUNTIME_VERSION or m.get("protocol_version")!=PROTOCOL_VERSION:raise ValueError("runtime_protocol_unsupported")
        _validate_source_provenance(m.get("source"))
        selection=m.get("selection")
        if not isinstance(selection,dict) or not isinstance(selection.get("qids"),list) or not isinstance(selection.get("count"),int):
            raise ValueError("selection_manifest_invalid")
        rows=m.get("animations")
        if not isinstance(rows,list) or not 1<=len(rows)<=MAX_ANIMATIONS:raise ValueError("animation_count_invalid")
        qids=set();paths=set();ordered=[]
        for row in rows:
            qid=_validate_manifest_record(row)
            if qid in qids:raise ValueError("manifest_qid_duplicate_or_invalid")
            qids.add(qid);ordered.append(qid)
            expected_paths={"entry_path":f"entries/{qid}.html","scene_path":f"scenes/{qid}.scene.json","source_record_path":f"source/questions/{qid}.json"}
            for field,expected_path in expected_paths.items():
                p=safe_path(row.get(field) or "")
                if p!=expected_path:raise ValueError("manifest_asset_path_invalid:"+field)
                if p in paths:raise ValueError("manifest_path_duplicate")
                paths.add(p)
                if p not in names:raise ValueError("manifest_asset_missing:"+p)
            for field,pathfield in [("entry_sha256","entry_path"),("scene_sha256","scene_path"),("source_record_sha256","source_record_path")]:
                expected=str(row.get(field) or "")
                if not re.fullmatch(r"[a-f0-9]{64}",expected,re.I):raise ValueError("manifest_hash_invalid")
                if sha256_bytes(z.read(row[pathfield]))!=expected.lower():raise ValueError("manifest_checksum_mismatch:"+qid)
            try:source=json.loads(z.read(row["source_record_path"]));scene=json.loads(z.read(row["scene_path"]))
            except Exception as exc:raise ValueError("motioncards_source_or_scene_json_invalid:"+qid) from exc
            q=source.get("question") if isinstance(source,dict) else None;integ=source.get("integrity") if isinstance(source,dict) else None
            provenance=source.get("provenance") if isinstance(source,dict) else None
            if provenance!=m.get("source"):raise ValueError("source_provenance_mismatch:"+qid)
            if not isinstance(q,dict) or not isinstance(integ,dict) or q.get("id")!=qid:raise ValueError("source_binding_mismatch:"+qid)
            if str(q.get("book_id"))!=row["book_id"] or int(q.get("version") or 0)!=row["book_version"] or str(q.get("chapter_id"))!=str(row["chapter_id"]):
                raise ValueError("source_identity_mismatch:"+qid)
            if content_hash(q)!=row["content_hash"].lower() or str(integ.get("content_hash","")).lower()!=row["content_hash"].lower():
                raise ValueError("source_binding_mismatch:"+qid)
            if str(integ.get("publisher_fingerprint","")).lower()!=row["publisher_fingerprint"].lower():raise ValueError("source_fingerprint_mismatch:"+qid)
            validate_scene(scene,qid,row["duration_ms"])
            voice=None
            if "voice" in row:
                v=row["voice"]
                if not isinstance(v,dict) or safe_path(v.get("path") or "")!=f"voice/{qid}.opus":raise ValueError("manifest_voice_path_invalid:"+qid)
                if v["path"] in paths:raise ValueError("manifest_path_duplicate")
                if v["path"] not in names:raise ValueError("manifest_asset_missing:"+v["path"])
                paths.add(v["path"]);voice=z.read(v["path"])
                expected={"path":v["path"],**validate_voice(voice,{"track_ms":v.get("track_ms"),"cues":v.get("cues")},row["duration_ms"])}
                if v!=expected:raise ValueError("manifest_voice_mismatch:"+qid)
            if bool(scene.get("replace",False))!=row["replace"]:raise ValueError("replace_intent_scene_manifest_mismatch:"+qid)
            if scene["takeaway"]!=row["final_panel"]["takeaway"]:raise ValueError("takeaway_scene_manifest_mismatch:"+qid)
            resolved=resolve_answer(q)
            if resolved["kind"]!=row["final_panel"].get("correct_answer_kind") or resolved["statements"]!=row["final_panel"].get("correct_answer_statements"):
                raise ValueError("final_answer_not_source_derived:"+qid)
            rebuilt=compile_scene(scene,voice=voice).encode()
            if rebuilt!=z.read(row["entry_path"]):raise ValueError("compiled_entry_scene_mismatch:"+qid)
            if sha256_bytes(rebuilt)!=row["entry_sha256"].lower():raise ValueError("compiled_entry_hash_mismatch:"+qid)
        if selection["qids"]!=ordered or selection["count"]!=len(ordered):raise ValueError("selection_manifest_mismatch")
        allowed=set(ALLOWED_ROOT_FILES)|paths
        extra=[n for n in names if n not in allowed and not n.startswith("reports/")]
        if extra:raise ValueError("unapproved_package_files:"+",".join(sorted(extra)[:5]))
        return m
