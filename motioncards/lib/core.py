from __future__ import annotations
import hashlib,json,math,re,unicodedata
from dataclasses import dataclass
from typing import Any
from .spec import QID_RE,validate_duration

HEX64=re.compile(r"^[a-f0-9]{64}$",re.I)

def canonical_json(value:Any)->str:
    if value is None:return "null"
    if value is True:return "true"
    if value is False:return "false"
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False,separators=(",",":"))
    if isinstance(value,int) and not isinstance(value,bool):return str(value)
    if isinstance(value,float):
        if not math.isfinite(value):raise TypeError("non_finite_number")
        if value==0:return "0"
        if value.is_integer():return str(int(value))
        # Exported question fields are text/integer dominated. This mirrors JSON.stringify
        # for normal finite decimal values and is guarded by shared golden vectors.
        return json.dumps(value,ensure_ascii=False,separators=(",",":")).replace("e+","e")
    if isinstance(value,list):return "["+",".join(canonical_json(x) for x in value)+"]"
    if isinstance(value,dict):
        return "{"+",".join(json.dumps(str(k),ensure_ascii=False)+":"+canonical_json(value[k]) for k in sorted(value))+ "}"
    raise TypeError("unsupported_json_value")

def sha256_text(text:str)->str:return hashlib.sha256(text.encode("utf-8")).hexdigest()
def content_hash(question:dict)->str:return sha256_text(canonical_json(question))

def norm(value:Any)->str:
    return re.sub(r"\s+"," ",unicodedata.normalize("NFKC",str(value or "")).lower()).strip()

def publisher_fingerprint_payload(q:dict)->str:
    # Exact key ordering produced by Python sort_keys=True / mcq-export-core.js.
    payload={"options":[norm(x) for x in q.get("options") or []],"stem":norm(q.get("stem")),"type":q.get("type")}
    return json.dumps(payload,ensure_ascii=False,separators=(",",":"),sort_keys=True)

def publisher_fingerprint(q:dict)->str:return sha256_text(publisher_fingerprint_payload(q))

def resolve_answer(q:dict)->dict:
    qtype=q.get("type");options=q.get("options")
    if not isinstance(options,list) or not options:raise ValueError("options_missing")
    answer=q.get("answer")
    def index(letter):
        if not isinstance(letter,str) or len(letter)!=1 or not "A"<=letter.upper()<="Z":raise ValueError("answer_encoding_unsupported")
        i=ord(letter.upper())-65
        if i>=len(options):raise ValueError("answer_option_out_of_range")
        return i
    if qtype in {"sba","emq"}:
        i=index(answer);return {"kind":qtype,"indexes":[i],"statements":[str(options[i])]}
    if qtype=="multi":
        if not isinstance(answer,list) or not answer:raise ValueError("multi_answer_encoding_unsupported")
        ids=[index(x) for x in answer]
        if len(set(ids))!=len(ids):raise ValueError("multi_answer_duplicate")
        return {"kind":"multi","indexes":ids,"statements":[str(options[i]) for i in ids]}
    if qtype=="mtf":
        if not isinstance(answer,list) or len(answer)!=len(options) or any(x not in {"T","F"} for x in answer):
            raise ValueError("mtf_answer_encoding_unsupported")
        return {"kind":"mtf","indexes":list(range(len(options))),"statements":[f"{options[i]} — {'True' if v=='T' else 'False'}" for i,v in enumerate(answer)]}
    raise ValueError("question_type_unsupported")

@dataclass
class AdaptedExport:
    envelopes:list[dict]
    questions:list[dict]
    integrity:dict[str,dict]
    book:dict
    chapters:list[dict]
    effective_scope:dict
    warnings:list[dict]
    provenance:dict

def adapt_exports(envelopes:list[dict])->AdaptedExport:
    if not envelopes:raise ValueError("export_missing")
    first=envelopes[0]
    for e in envelopes:
        if e.get("export_type")!="kafu_mcq_text_export" or e.get("schema_version")!=1:raise ValueError("export_contract_unsupported")
    def ident(e):
        b=e.get("book") or {};s=e.get("scope") or {};src=e.get("source") or {}
        return (str(b.get("id") or s.get("book_id") or ""),int(b.get("version") or s.get("book_version") or 0),src.get("catalog_sha256"),src.get("index_sha256"))
    identity=ident(first)
    if not identity[0] or identity[1]<1:raise ValueError("book_identity_missing")
    for e in envelopes[1:]:
        if ident(e)!=identity:raise ValueError("inconsistent_export_snapshots")
    questions=[];integrity={};seen=set()
    for e in envelopes:
        rows=e.get("questions")
        if not isinstance(rows,list):raise ValueError("questions_missing")
        ints={x.get("qid"):x for x in (e.get("export_metadata",{}).get("question_integrity") or []) if isinstance(x,dict)}
        for q in rows:
            if not isinstance(q,dict):raise ValueError("question_invalid")
            qid=q.get("id")
            if not QID_RE.fullmatch(str(qid or "")):raise ValueError("qid_invalid")
            if qid in seen:raise ValueError("duplicate_qid")
            seen.add(qid)
            if str(q.get("book_id"))!=identity[0] or int(q.get("version") or 0)!=identity[1]:raise ValueError(f"question_identity_conflict:{qid}")
            row=ints.get(qid)
            if not row:raise ValueError(f"integrity_missing:{qid}")
            actual=content_hash(q)
            if not HEX64.fullmatch(str(row.get("content_hash") or "")) or row["content_hash"].lower()!=actual:raise ValueError(f"content_hash_mismatch:{qid}")
            if row.get("content_hash_algorithm")!="SHA-256" or row.get("content_hash_canonicalization")!="kafu-question-canonical-json-v1":raise ValueError(f"content_hash_contract_mismatch:{qid}")
            supplied=row.get("publisher_fingerprint")
            expected=publisher_fingerprint(q)
            if not HEX64.fullmatch(str(supplied or "")) or supplied.lower()!=expected:
                # Publisher may have supplied an authoritative fingerprint field in q.
                authoritative=q.get("publisher_fingerprint") or q.get("fingerprint")
                if not (HEX64.fullmatch(str(authoritative or "")) and supplied and supplied.lower()==str(authoritative).lower()):
                    raise ValueError(f"publisher_fingerprint_mismatch:{qid}")
            resolve_answer(q)
            integrity[qid]=dict(row)
            questions.append(q)
    book=dict(first.get("book") or {})
    if str(book.get("id"))!=identity[0] or int(book.get("version") or 0)!=identity[1]:raise ValueError("book_identity_conflict")
    # Several chapter exports of one book snapshot may be packaged together: merge their chapter metadata.
    chapters=[];chapter_by_id={}
    for e in envelopes:
        for ch in list(e.get("chapters") or (e.get("book") or {}).get("chapters") or []):
            if isinstance(ch,dict) and str(ch.get("id")) not in chapter_by_id:chapter_by_id[str(ch.get("id"))]=ch;chapters.append(ch)
    for q in questions:
        ch=chapter_by_id.get(str(q.get("chapter_id")))
        if not ch:raise ValueError(f"chapter_missing:{q['id']}")
        if isinstance(ch.get("qids"),list) and q["id"] not in [str(x) for x in ch["qids"]]:raise ValueError(f"qid_not_in_chapter_manifest:{q['id']}")
    warnings=[]
    raw_scope=dict(first.get("scope") or {})
    actual_chapters=[]
    for q in questions:
        x=str(q.get("chapter_id"))
        if x not in actual_chapters:actual_chapters.append(x)
    effective={"type":"records","book_id":identity[0],"book_version":identity[1],"chapter_ids":actual_chapters,"question_count":len(questions),"qids":[q["id"] for q in questions]}
    if raw_scope.get("type")=="book" and len(actual_chapters)==1:
        ch=chapter_by_id.get(actual_chapters[0])
        if ch and int(ch.get("questions") or -1)==len(questions) and int(book.get("questions") or len(questions))>len(questions):
            warnings.append({"code":"scope_label_mismatch","message":"Export labels the selection as whole-book, but supplied records exactly match one chapter. Using actual supplied records only.","raw_scope":raw_scope,"derived_chapter_id":ch.get("id")})
            effective.update(type="chapter",chapter_id=ch.get("id"),chapter_title=ch.get("title"))
    # A part's aggregate total does not need to equal this file's record count.
    for e in envelopes:
        part=e.get("part")
        if part is None:
            claimed=e.get("exported_question_count")
            if isinstance(claimed,int) and claimed!=len(e.get("questions") or []) and not warnings:
                raise ValueError("exported_question_count_conflict")
        elif not isinstance(part,dict) or int(part.get("question_count") or -1)!=len(e.get("questions") or []):
            raise ValueError("partition_question_count_conflict")
    src=first.get("source") or {}
    provenance={"kind":src.get("kind"),"catalog_url":src.get("catalog_url"),"catalog_sha256":src.get("catalog_sha256"),"index_url":src.get("index_url"),"index_sha256":src.get("index_sha256"),"snapshot_pinned":src.get("snapshot_pinned")}
    return AdaptedExport(envelopes,questions,integrity,book,chapters,effective,warnings,provenance)

def select_questions(bundle:AdaptedExport,qids:list[str]|None,count:int|None,duration_ms:int|None,overrides:dict[str,int]|None=None,inspected_images:set[str]|None=None):
    overrides=overrides or {};inspected_images=inspected_images or set()
    if qids and count is not None and count!=len(qids):raise ValueError("count_qid_conflict")
    if not qids and count is None:raise ValueError("selection_required")
    by_id={q["id"]:q for q in bundle.questions}
    requested=list(qids) if qids else [q["id"] for q in bundle.questions[:count]]
    if len(requested)!=len(set(requested)):raise ValueError("requested_qid_duplicate")
    if count is not None and (not isinstance(count,int) or count<1 or count>len(bundle.questions)):raise ValueError("requested_count_unavailable")
    missing=[x for x in requested if x not in by_id]
    if missing:raise ValueError("requested_qid_unavailable:"+",".join(missing))
    selected=[];blocked=[]
    for qid in requested:
        q=by_id[qid]
        ms=overrides.get(qid,duration_ms)
        if ms is None:raise ValueError(f"duration_missing:{qid}")
        validate_duration(ms)
        try:answer=resolve_answer(q)
        except ValueError as exc:
            blocked.append({"qid":qid,"reason":str(exc)});continue
        image_refs=list(q.get("images") or [])+list(q.get("explanation_images") or [])
        if image_refs and qid not in inspected_images:
            blocked.append({"qid":qid,"reason":"source_image_bytes_not_inspected"});continue
        selected.append({"qid":qid,"duration_ms":ms,"question":q,"integrity":bundle.integrity[qid],"answer":answer})
    if blocked:raise ValueError("blocked_requested_items:"+json.dumps(blocked,separators=(",",":")))
    return selected
