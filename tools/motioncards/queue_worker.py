#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.http_client import request_json,download
from tools.motioncards.publish import apply_packages,plan_packages,apply_management
from motioncards.lib.multipart import validate_package_part,combine_parts
from motioncards.lib.spec import parse_package_filename

MAX_ZIP=19*1024*1024

class Queue:
    def __init__(self):
        self.base=os.environ["QUEUE_API_URL"].rstrip("/")+"/internal/motioncards/"
        token=os.environ["QUEUE_API_TOKEN"].strip()
        self.headers={"Authorization":"Bearer "+token}
    def call(self,path,payload=None):
        return request_json(self.base+path,step="motioncards.queue."+path,method="POST",payload=payload or {},headers=self.headers)
    def notify(self,text):
        return self.call("notify",{"text":str(text)[:3500]})

def telegram_file(file_id,target):
    token=os.environ["BOT_TOKEN"]
    data=request_json("https://api.telegram.org/bot"+token+"/getFile",step="motioncards.telegram.getFile",method="POST",payload={"file_id":file_id})
    fp=data.get("result",{}).get("file_path") if data.get("ok") else None
    if not fp:raise ValueError("telegram_get_file_failed")
    download("https://api.telegram.org/file/bot"+token+"/"+fp,target,step="motioncards.telegram.download",timeout=90,max_bytes=MAX_ZIP)

def tree_sha(site:Path)->str:
    h=hashlib.sha256()
    for p in sorted(x for x in site.rglob("*") if x.is_file()):
        h.update(p.relative_to(site).as_posix().encode()+b"\0");h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def validate_downloaded_identity(group:dict,parts:list[dict],packages:list[Path]):
    total=int(group["part_total"]);package_id=str(group["package_id"]);revision=int(group["revision"])
    if len(parts)!=total or len(packages)!=total:raise ValueError("incomplete_motioncards_group")
    expected=list(range(1,total+1))
    if [int(p["part_index"]) for p in parts]!=expected:raise ValueError("motioncards_part_sequence_invalid")
    for row,path in zip(parts,packages):
        if path.stat().st_size!=int(row["file_size"]):raise ValueError("motioncards_download_size_mismatch")
        parsed=parse_package_filename(str(row["filename"]))
        if not parsed:raise ValueError("motioncards_filename_identity_invalid")
        if parsed["group_key"]!=group["group_key"] or parsed["package_id"]!=package_id or parsed["package_revision"]!=revision:
            raise ValueError("motioncards_filename_group_mismatch")
        if parsed["part"]!=int(row["part_index"]) or parsed["total"]!=total or int(row["part_total"])!=total:
            raise ValueError("motioncards_filename_part_mismatch")
        manifest=validate_package_part(path)
        if manifest["package_id"]!=package_id or int(manifest["package_revision"])!=revision:raise ValueError("motioncards_manifest_group_mismatch")
        mp=manifest.get("multipart")
        if total==1:
            if mp is not None:raise ValueError("motioncards_single_filename_cannot_publish_multipart")
        else:
            if not isinstance(mp,dict):raise ValueError("motioncards_multipart_manifest_required")
            if int(mp["part_index"])!=parsed["part"] or int(mp["total_parts"])!=total:raise ValueError("motioncards_manifest_part_mismatch")
    combined,_,_=combine_parts(packages)
    if combined["package_id"]!=package_id or int(combined["package_revision"])!=revision:raise ValueError("motioncards_combined_identity_mismatch")
    if sum(int(p["file_size"]) for p in parts)!=sum(p.stat().st_size for p in packages):raise ValueError("motioncards_batch_size_mismatch")
    return combined

def _cards(result:dict):
    rows=[]
    for x in result.get("affected") or []:
        if not isinstance(x,dict):continue
        rows.append({k:x.get(k) for k in ["book_id","book_version","chapter_id","qid","content_hash","package_id","package_revision","entry_sha256","entry_url","duration_ms","final_panel"]}|{"active":bool(x.get("active",True))})
    return rows

def _write_meta(work:Path,meta:dict):
    (work/"result.json").write_text(json.dumps(meta,indent=2)+"\n");print(json.dumps(meta))

def prepare(work:Path,allow_initial:bool):
    q=Queue();item=q.call("claim")
    if item.get("kind")=="empty":
        print(json.dumps({"empty":True}));return 0
    kind=item.get("kind");lease=item.get("lease_token")
    work.mkdir(parents=True,exist_ok=True);state=work/"state.json";site=work/"site"
    if not state.exists():
        if not allow_initial:raise ValueError("motioncards_state_missing_owner_initialization_required")
        site.mkdir(parents=True,exist_ok=True)
    if kind=="motioncards-admin":
        op=item["operation"]
        try:
            result=apply_management({"operation_id":op["operation_id"],"kind":op["kind"],"qid":op["qid"],"book_id":op["book_id"],
                                     "book_version":op["book_version"],"chapter_id":op["chapter_id"],"expected_active_digest":op.get("expected_active_digest"),
                                     "target_digest":op.get("target_digest")},state,site)
            build=json.loads((site/"build-info.json").read_text());cards=_cards(result)
            _write_meta(work,{"empty":False,"kind":"admin","operation_id":op["operation_id"],"operation_kind":op["kind"],"lease_token":lease,
                              "duplicate":bool(result.get("duplicate")),"needs_deploy":bool(result.get("changed",True)),"state_sha256":build["state_sha256"],
                              "tree_sha256":tree_sha(site),"cards":cards,"reconciliation":result.get("reconciliation") or []})
            return 0
        except Exception as exc:
            safe=(type(exc).__name__+":"+str(exc))[:350]
            q.call("finish",{"operation_id":op["operation_id"],"lease_token":lease,"ok":False,"error":safe})
            try:q.notify("❌ MotionCards "+op["kind"]+" "+op["qid"]+" failed: "+safe)
            except Exception as notify_exc:print("warning: MotionCards management notification failed:",type(notify_exc).__name__,file=sys.stderr)
            raise
    if kind!="motioncards":raise ValueError("unexpected_motioncards_claim")
    group=item["group"]
    try:
        parts=item.get("parts") or [];packages=[]
        for part in parts:
            package=work/part["filename"];telegram_file(part["telegram_file_id"],package);packages.append(package)
        validate_downloaded_identity(group,parts,packages)
        plan=plan_packages(packages,state)
        if plan["replacements"] and not group.get("replacement_auth_json"):
            staged=q.call("candidate",{"group_key":group["group_key"],"lease_token":lease,"candidate_digest":plan["package_sha256"],"targets":plan["replacements"]})
            print(json.dumps({"awaiting_confirmation":True,"group_key":group["group_key"],"candidate_digest":plan["package_sha256"],"targets":len(plan["replacements"]),"token":staged.get("token")}))
            return 0
        authorizations=None
        if group.get("replacement_auth_json"):
            if str(group.get("candidate_digest") or "").lower()!=str(plan["package_sha256"]).lower():raise ValueError("motioncards_confirmed_candidate_digest_changed")
            raw_auth=json.loads(group["replacement_auth_json"])
            if isinstance(raw_auth,dict) and "confirmation_token" in raw_auth and "targets" in raw_auth:
                token=str(raw_auth.get("confirmation_token") or "")
                if not token or not isinstance(raw_auth.get("targets"),dict):raise ValueError("motioncards_replacement_authorization_invalid")
                authorizations=raw_auth["targets"]
            else:
                authorizations=raw_auth
        result=apply_packages(packages,state,site,replacement_authorizations=authorizations)
        build=json.loads((site/"build-info.json").read_text());cards=_cards(result)
        _write_meta(work,{"empty":False,"kind":"package","group_key":group["group_key"],"lease_token":lease,"package_sha256":result["package_sha256"],
                          "animations":result["animations"],"duplicate":bool(result.get("duplicate")),"needs_deploy":bool(result.get("changed",True)),
                          "state_sha256":build["state_sha256"],"tree_sha256":tree_sha(site),"cards":cards,"reconciliation":result.get("reconciliation") or []})
        return 0
    except Exception as exc:
        safe=(type(exc).__name__+":"+str(exc))[:350]
        q.call("finish",{"group_key":group["group_key"],"lease_token":lease,"ok":False,"error":safe})
        try:q.notify("❌ MotionCards "+group["group_key"]+" failed: "+safe)
        except Exception as notify_exc:print("warning: MotionCards failure notification failed:",type(notify_exc).__name__,file=sys.stderr)
        raise

def finish(work:Path,ok:bool,error=""):
    meta=json.loads((work/"result.json").read_text());q=Queue()
    if meta.get("kind")=="admin":
        payload={"operation_id":meta["operation_id"],"lease_token":meta["lease_token"],"ok":ok}
        if ok:
            payload["card"]=meta["cards"][0]
            payload["duplicate"]=bool(meta.get("duplicate",False))
            if payload["duplicate"]:payload["reconciliation"]=meta.get("reconciliation") or []
        else:payload["error"]=error[:400]
        q.call("finish",payload)
        label=meta["operation_kind"]+" "+meta["cards"][0]["qid"] if meta.get("cards") else meta["operation_id"]
    else:
        payload={"group_key":meta["group_key"],"lease_token":meta["lease_token"],"ok":ok}
        if ok:
            payload.update(package_sha256=meta["package_sha256"],animations=meta["animations"],cards=meta["cards"],duplicate=bool(meta.get("duplicate",False)))
            if payload["duplicate"]:payload["reconciliation"]=meta.get("reconciliation") or []
        else:payload["error"]=error[:400]
        q.call("finish",payload);label=meta["group_key"]
    try:q.notify(("✅ " if ok else "❌ ")+"MotionCards "+label+(" published." if ok else " failed: "+error[:250]))
    except Exception as notify_exc:print("warning: MotionCards notification failed after queue acknowledgement:",type(notify_exc).__name__,file=sys.stderr)

def has_work():
    data=Queue().call("has-ready");print(json.dumps(data));return 0 if data.get("ready") else 3

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("prepare");p.add_argument("--work",type=Path,required=True);p.add_argument("--allow-initial",action="store_true")
    f=sub.add_parser("finish");f.add_argument("--work",type=Path,required=True);f.add_argument("--ok",action="store_true");f.add_argument("--error",default="")
    sub.add_parser("has-work");a=ap.parse_args()
    if a.cmd=="prepare":return prepare(a.work,a.allow_initial)
    if a.cmd=="has-work":return has_work()
    finish(a.work,a.ok,a.error);return 0
if __name__=="__main__":raise SystemExit(main())
