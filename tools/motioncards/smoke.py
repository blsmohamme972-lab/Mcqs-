#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys,time,urllib.error,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.http_client import request_json,HttpStepError

CSP_REQUIRED=["default-src 'none'","connect-src 'none'","worker-src 'none'","form-action 'none'","sandbox allow-scripts"]
MAX_ENTRY=2*1024*1024

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def fetch_exact(url,attempts=3):
    # A freshly staged preview can be slow on its first request: retry timeouts and
    # connection errors (not HTTP answers) before failing the publish.
    req=urllib.request.Request(url,method="GET",headers={"User-Agent":"kafu-motioncards-smoke/1.0"})
    for attempt in range(1,attempts+1):
        try:
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=45) as r:
                raw=r.read(MAX_ENTRY+1)
                return r.status,r.geturl(),r.headers,raw
        except urllib.error.HTTPError as exc:
            if 300<=exc.code<400:raise ValueError("motioncards_entry_redirect:"+str(exc.code)) from None
            raise
        except (TimeoutError,urllib.error.URLError,ConnectionError):
            if attempt==attempts:raise
            time.sleep(5*attempt)

def check_entry(base,row):
    path=urlsplit(row["entry_url"]).path;expected=base+path
    status,final,headers,raw=fetch_exact(expected)
    if status!=200 or final!=expected or len(raw)>MAX_ENTRY:raise ValueError("motioncards_entry_invalid")
    if hashlib.sha256(raw).hexdigest()!=str(row["entry_sha256"]).lower():raise ValueError("motioncards_entry_sha256_mismatch:"+row["qid"])
    if "text/html" not in str(headers.get("Content-Type","")).lower():raise ValueError("motioncards_entry_content_type_invalid")
    csp=headers.get("Content-Security-Policy","")
    for token in CSP_REQUIRED:
        if token not in csp:raise ValueError("motioncards_csp_missing:"+token)
    if headers.get("X-Content-Type-Options")!="nosniff":raise ValueError("motioncards_nosniff_missing")
    if headers.get("Referrer-Policy")!="no-referrer":raise ValueError("motioncards_referrer_policy_missing")
    return len(raw)

def load_index(base,meta,card):
    book_id=str(card["book_id"]);version=int(card["book_version"]);qid=str(card["qid"])
    url=base+"/indexes/"+book_id+"/v"+str(version)+"/index.json?state="+meta["state_sha256"]
    try:
        return request_json(url,step="motioncards.smoke.index."+qid)
    except HttpStepError as exc:
        if card.get("active") is False and exc.status==404:
            return {"animations":{}}
        raise

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--url",required=True);ap.add_argument("--result",required=True);a=ap.parse_args()
    base=a.url.rstrip("/");meta=json.load(open(a.result))
    build=request_json(base+"/build-info.json?state="+meta["state_sha256"],step="motioncards.smoke.build")
    if build.get("state_sha256")!=meta["state_sha256"]:raise ValueError("motioncards_state_not_live")
    cards=meta.get("cards")
    if not isinstance(cards,list) or not cards:raise ValueError("motioncards_smoke_affected_cards_missing")
    entry_bytes=0;active=removed=0
    for card in cards:
        qid=str(card["qid"])
        idx=load_index(base,meta,card)
        row=idx.get("animations",{}).get(qid)
        if card.get("active") is False:
            removed+=1
            if row is not None:raise ValueError("motioncards_removed_mapping_still_live:"+qid)
            continue
        active+=1
        if not row:raise ValueError("motioncards_index_affected_mapping_missing:"+qid)
        for field in ["book_id","book_version","chapter_id","qid","content_hash","entry_sha256","entry_url"]:
            if str(row.get(field))!=str(card.get(field)):raise ValueError("motioncards_index_affected_mapping_mismatch:"+qid+":"+field)
        entry_bytes+=check_entry(base,row)
    print(json.dumps({"motioncards_smoke":"PASS","state_sha256":meta["state_sha256"],"active_cards":active,"removed_cards":removed,"entry_bytes":entry_bytes}))
if __name__=="__main__":main()
