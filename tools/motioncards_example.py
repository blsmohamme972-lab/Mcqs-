#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motioncards.lib.core import content_hash,publisher_fingerprint,adapt_exports
from motioncards.lib.package import scaffold_workspace
from motioncards.lib.multipart import build_package_set,validate_package_part

def q(qid,qtype,options,answer,stem):
    return {"id":qid,"book_id":"MOTIONCARDS-FIXTURE","version":1,"chapter_id":1,"type":qtype,"stem":stem,"lead_in":"",
            "options":options,"answer":answer,"explanation":"Synthetic educational fixture only.","images":[],"explanation_images":[],"status":"source_verified"}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    qs=[q("Q000000001","sba",["Higher to lower pressure","Lower to higher pressure","No movement"],"A","Which direction follows a pressure gradient?"),
        q("Q000000002","multi",["Activation","Directional movement","Random looping","Final effect"],["A","B"],"Choose two stages used in this synthetic sequence.")]
    ch={"id":1,"title":"Synthetic relationships","questions":2,"qids":[x["id"] for x in qs],"url":"https://kafu-content-1.blsmohamme97.workers.dev/fixture/chapter.json"}
    ints=[{"qid":x["id"],"publisher_fingerprint":publisher_fingerprint(x),"publisher_fingerprint_source":"recomputed_from_publish_py_fingerprint_v1",
           "content_hash":content_hash(x),"content_hash_algorithm":"SHA-256","content_hash_canonicalization":"kafu-question-canonical-json-v1"} for x in qs]
    envelope={"export_type":"kafu_mcq_text_export","schema_version":1,"exported_at":"2026-10-06T00:00:00Z",
      "source":{"kind":"published","catalog_url":"https://kafu-content-1.blsmohamme97.workers.dev/catalog.json","catalog_sha256":"0"*64,"snapshot_pinned":True},
      "scope":{"type":"book","book_id":"MOTIONCARDS-FIXTURE","book_version":1},
      "book":{"id":"MOTIONCARDS-FIXTURE","title":"Kafu MotionCards Synthetic Fixture","version":1,"questions":2,"chapters":[ch]},
      "chapters":[ch],"expected_question_count":2,"exported_question_count":2,"questions":qs,"export_metadata":{"question_integrity":ints}}
    export=a.out/"synthetic-export.json";export.write_text(json.dumps(envelope,ensure_ascii=False,indent=2)+"\n")
    bundle=adapt_exports([envelope]);ws=a.out/"workspace"
    scaffold_workspace(bundle,ws,"FIXTURE-DEMO",1,[x["id"] for x in qs],None,None,{"Q000000001":8000,"Q000000002":6000})
    shutil.copy2(ROOT/"motioncards/examples/flow.scene.json",ws/"scenes/Q000000001.scene.json")
    shutil.copy2(ROOT/"motioncards/examples/sequence.scene.json",ws/"scenes/Q000000002.scene.json")
    paths=build_package_set(bundle,ws,a.out/"MCARDS_FIXTURE-DEMO_r1.zip")
    for path in paths:validate_package_part(path)
    print(json.dumps({"export":str(export),"zips":[str(x) for x in paths],"animations":2},indent=2))
if __name__=="__main__":main()
