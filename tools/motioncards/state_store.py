#!/usr/bin/env python3
from __future__ import annotations
import argparse,gzip,hashlib,json,os,shutil,subprocess,tarfile,tempfile,urllib.error,urllib.request
from pathlib import Path

TAG="kafu-motioncards-state"
PROD="https://kafu-motioncards.blsmohamme97.workers.dev"
HEX64=set("0123456789abcdef")
BOOTSTRAP_BODY=b"Kafu MotionCards is initializing."

def run(*args,check=True):
    p=subprocess.run(args,text=True,capture_output=True)
    if check and p.returncode:raise RuntimeError("command_failed:"+args[0]+":"+p.stderr[-500:])
    return p

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def state_digest(data:dict)->str:
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def tree_digest(site:Path)->str:
    h=hashlib.sha256()
    for p in sorted(x for x in site.rglob("*") if x.is_file()):
        h.update(p.relative_to(site).as_posix().encode()+b"\0");h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def _hex64(value)->bool:
    s=str(value or "").lower()
    return len(s)==64 and all(ch in HEX64 for ch in s)

def release_status():
    p=run("gh","release","view",TAG,"--json","id",check=False)
    if p.returncode==0:return "present"
    detail=(p.stderr+"\n"+p.stdout).lower()
    # Only explicit release-resolution failures mean "no state yet".
    # Generic 404/not-found text can also mean repository/auth/network denial.
    absent=any(x in detail for x in ["release not found","could not resolve to a release"])
    if absent:return "absent"
    raise RuntimeError("motioncards_state_release_lookup_failed:"+detail[-300:])

def release_assets()->set[str]:
    p=run("gh","release","view",TAG,"--json","assets","--jq",".assets[].name")
    return {x.strip() for x in p.stdout.splitlines() if x.strip()}

def download_one(work:Path,name:str):
    target=work/"release"/name
    if target.exists():return target
    run("gh","release","download",TAG,"--pattern",name,"--dir",str(work/"release"))
    if not target.is_file():raise RuntimeError("motioncards_release_asset_missing:"+name)
    return target

def upload_immutable(work:Path,path:Path,assets:set[str]):
    if path.name in assets:
        with tempfile.TemporaryDirectory(prefix="motioncards-remote-check-") as td:
            run("gh","release","download",TAG,"--pattern",path.name,"--dir",td)
            remote=Path(td)/path.name
            if not remote.is_file() or sha256_file(remote)!=sha256_file(path):
                raise RuntimeError("motioncards_candidate_asset_conflict:"+path.name)
        return
    run("gh","release","upload",TAG,str(path))
    assets.add(path.name)

def live_state(allow_bootstrap:bool=False):
    try:
        req=urllib.request.Request(PROD+"/build-info.json?restore=1",headers={"User-Agent":"kafu-motioncards-state/1.0"})
        with urllib.request.urlopen(req,timeout=15) as r:
            if r.status!=200:raise RuntimeError("motioncards_live_state_http_"+str(r.status))
            data=json.load(r);value=data.get("state_sha256","")
            if not _hex64(value):raise RuntimeError("motioncards_live_state_invalid")
            return "present",value.lower()
    except urllib.error.HTTPError as exc:
        if exc.code==404:return "absent",""
        if exc.code==503 and allow_bootstrap:
            try:body=exc.read(256).strip()
            except Exception:body=b""
            retry_after=str(exc.headers.get("Retry-After","") if exc.headers else "").strip()
            if body==BOOTSTRAP_BODY and retry_after=="60":return "bootstrap",""
        raise RuntimeError("motioncards_live_state_http_"+str(exc.code)) from exc
    except (urllib.error.URLError,TimeoutError,OSError) as exc:
        raise RuntimeError("motioncards_live_state_unavailable") from exc

def _safe_extract(tar_path:Path,target:Path):
    target.mkdir(parents=True,exist_ok=True);root=target.resolve()
    with tarfile.open(tar_path,"r:gz") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk() or member.isdev() or not (member.isfile() or member.isdir()):
                raise RuntimeError("motioncards_state_tar_link_or_special")
            dest=(target/member.name).resolve()
            if dest!=root and root not in dest.parents:raise RuntimeError("motioncards_state_tar_traversal")
            if member.isdir():
                dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            src=tar.extractfile(member)
            if src is None:raise RuntimeError("motioncards_state_tar_member_unreadable")
            with src,dest.open("wb") as out:shutil.copyfileobj(src,out)
            os.chmod(dest,0o644)

def _write_deterministic_site_archive(site:Path,target:Path):
    with target.open("wb") as raw,gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode="w") as tar:
        for p in sorted(x for x in site.rglob("*") if x.is_file()):
            rel=p.relative_to(site).as_posix();info=tar.gettarinfo(str(p),arcname=rel)
            info.mtime=0;info.uid=0;info.gid=0;info.uname="";info.gname="";info.mode=0o644
            with p.open("rb") as f:tar.addfile(info,f)

def _candidate_names(state:str):
    return "state-"+state+".json","site-"+state+".tar.gz","candidate-"+state+".json"

def verify_candidate(work:Path,state:str):
    if not _hex64(state):raise RuntimeError("motioncards_candidate_state_invalid")
    state_name,site_name,meta_name=_candidate_names(state)
    state_file=download_one(work,state_name);site_file=download_one(work,site_name);meta_file=download_one(work,meta_name)
    meta=json.loads(meta_file.read_text())
    required={"schema":1,"state_sha256":state}
    if any(meta.get(k)!=v for k,v in required.items()):raise RuntimeError("motioncards_candidate_metadata_identity_invalid")
    for field in ["state_file_sha256","site_archive_sha256","tree_sha256"]:
        if not _hex64(meta.get(field)):raise RuntimeError("motioncards_candidate_metadata_hash_invalid:"+field)
    if sha256_file(state_file)!=meta["state_file_sha256"]:raise RuntimeError("motioncards_candidate_state_artifact_hash_mismatch")
    if sha256_file(site_file)!=meta["site_archive_sha256"]:raise RuntimeError("motioncards_candidate_site_artifact_hash_mismatch")
    data=json.loads(state_file.read_text())
    if state_digest(data)!=state:raise RuntimeError("motioncards_candidate_state_content_hash_mismatch")
    extracted=work/("verified-site-"+state)
    shutil.rmtree(extracted,ignore_errors=True);_safe_extract(site_file,extracted)
    if tree_digest(extracted)!=meta["tree_sha256"]:raise RuntimeError("motioncards_candidate_tree_hash_mismatch")
    build=json.loads((extracted/"build-info.json").read_text())
    if build.get("state_sha256")!=state:raise RuntimeError("motioncards_candidate_build_info_mismatch")
    return data,extracted,meta

def _install_verified(work:Path,state:str):
    data,site,_=verify_candidate(work,state)
    shutil.rmtree(work/"site",ignore_errors=True);shutil.copytree(site,work/"site")
    (work/"state.json").write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    return data

def _write_active(work:Path,state:str):
    active=work/"active.json";active.write_text(json.dumps({"schema":1,"state_sha256":state})+"\n")
    run("gh","release","upload",TAG,str(active),"--clobber")

def _write_pending(work:Path,state:str):
    pending=work/"pending.json";pending.write_text(json.dumps({"schema":1,"state_sha256":state})+"\n")
    run("gh","release","upload",TAG,str(pending),"--clobber")

def _candidate_states(assets:set[str])->list[str]:
    out=[]
    for name in assets:
        if not (name.startswith("candidate-") and name.endswith(".json")):continue
        state=name[len("candidate-"):-len(".json")].lower()
        if _hex64(state) and set(_candidate_names(state)).issubset(assets):out.append(state)
    return sorted(set(out))

def _write_empty_retry_base(work:Path):
    data={"schema":1,"packages":{},"animations":{},"history":{},"operations":{}}
    (work/"state.json").write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    shutil.rmtree(work/"site",ignore_errors=True);(work/"site").mkdir(parents=True)

def restore(work:Path,allow_initial:bool):
    shutil.rmtree(work,ignore_errors=True);(work/"site").mkdir(parents=True);(work/"release").mkdir()
    status=release_status()
    assets=release_assets() if status=="present" else set()
    allow_bootstrap=allow_initial and (status=="absent" or "active.json" not in assets)
    live_kind,live=live_state(allow_bootstrap=allow_bootstrap)
    if status=="absent":
        if live_kind=="present":raise RuntimeError("live_motioncards_state_has_no_durable_release")
        if not allow_initial:raise RuntimeError("motioncards_state_missing_owner_initialization_required")
        print(json.dumps({"has_state":False,"recovery":"initial-bootstrap" if live_kind=="bootstrap" else "initial-empty"}));return False

    active_name="active.json"
    if active_name not in assets:
        if live_kind=="present":
            needed=set(_candidate_names(live))
            if not needed.issubset(assets):raise RuntimeError("live_motioncards_state_has_no_durable_candidate")
            _install_verified(work,live);_write_active(work,live)
            print(json.dumps({"has_state":True,"state_sha256":live,"recovery":"promotion-before-pointer"}));return True
        candidates=_candidate_states(assets)
        pending_state=""
        if "pending.json" in assets:
            pending_file=download_one(work,"pending.json")
            pending=json.loads(pending_file.read_text());pending_state=str(pending.get("state_sha256","")).lower()
            if not _hex64(pending_state) or pending_state not in candidates:raise RuntimeError("motioncards_pending_pointer_invalid")
        elif len(candidates)==1:
            pending_state=candidates[0]
        elif len(candidates)>1:
            raise RuntimeError("motioncards_initial_candidate_ambiguous")
        if pending_state:
            # Verify the durable candidate, but do NOT install it as active: promotion never succeeded.
            # Rebuild from the empty initial base so the same queued package is revalidated and redeployed.
            verify_candidate(work,pending_state);_write_empty_retry_base(work)
            print(json.dumps({"has_state":False,"recovery":"initial-candidate-retry-base","candidate_state_sha256":pending_state}));return False
        if not allow_initial:raise RuntimeError("motioncards_active_pointer_missing_owner_recovery_required")
        print(json.dumps({"has_state":False,"recovery":"initial-empty"}));return False

    active_file=download_one(work,active_name)
    pointer=json.loads(active_file.read_text());active=str(pointer.get("state_sha256","")).lower()
    if not _hex64(active):raise RuntimeError("motioncards_active_pointer_invalid")
    if live_kind!="present":raise RuntimeError("motioncards_production_state_missing_for_active_pointer")
    if live!=active:
        needed=set(_candidate_names(live))
        if not needed.issubset(assets):raise RuntimeError("live_motioncards_state_has_no_durable_candidate")
        _install_verified(work,live);_write_active(work,live)
        print(json.dumps({"has_state":True,"state_sha256":live,"recovery":"promotion-before-pointer"}));return True
    _install_verified(work,active)
    print(json.dumps({"has_state":True,"state_sha256":active,"recovery":"active"}));return True

def persist_candidate(work:Path):
    result=json.loads((work/"result.json").read_text());state=str(result["state_sha256"]).lower()
    if not _hex64(state):raise RuntimeError("motioncards_result_state_invalid")
    data=json.loads((work/"state.json").read_text())
    if state_digest(data)!=state:raise RuntimeError("motioncards_result_state_hash_mismatch")
    actual_tree=tree_digest(work/"site")
    if actual_tree!=result.get("tree_sha256"):raise RuntimeError("motioncards_result_tree_hash_mismatch")
    state_asset=work/("state-"+state+".json");site_asset=work/("site-"+state+".tar.gz");meta_asset=work/("candidate-"+state+".json")
    state_asset.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    _write_deterministic_site_archive(work/"site",site_asset)
    meta={"schema":1,"state_sha256":state,"tree_sha256":actual_tree,"state_file_sha256":sha256_file(state_asset),"site_archive_sha256":sha256_file(site_asset),
          "group_key":result.get("group_key"),"package_sha256":result.get("package_sha256")}
    meta_asset.write_text(json.dumps(meta,sort_keys=True,indent=2)+"\n")
    status=release_status()
    if status=="absent":
        run("gh","release","create",TAG,"--title","Kafu MotionCards state","--notes","Independent MotionCards state; not book content.")
        assets=set()
    else:assets=release_assets()
    for asset in [state_asset,site_asset,meta_asset]:upload_immutable(work,asset,assets)
    _write_pending(work,state)
    print(state)

def activate(work:Path):
    result=json.loads((work/"result.json").read_text());state=str(result["state_sha256"]).lower()
    # Candidate must already be persisted and verifiable before the mutable pointer advances.
    assets=release_assets()
    if not set(_candidate_names(state)).issubset(assets):raise RuntimeError("motioncards_candidate_not_persisted")
    _install_verified(work,state);_write_active(work,state);print(state)

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    r=sub.add_parser("restore");r.add_argument("--work",type=Path,required=True);r.add_argument("--allow-initial",action="store_true")
    p=sub.add_parser("persist-candidate");p.add_argument("--work",type=Path,required=True)
    a=sub.add_parser("activate");a.add_argument("--work",type=Path,required=True)
    x=ap.parse_args()
    if x.cmd=="restore":restore(x.work,x.allow_initial)
    elif x.cmd=="persist-candidate":persist_candidate(x.work)
    else:activate(x.work)
if __name__=="__main__":main()
