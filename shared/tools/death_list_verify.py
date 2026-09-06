#!/usr/bin/env python3
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

S=Path("novels/death-list/platform-sync"); TITLE="每天零点我都会收到一份死亡名单"
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def before(p):
    r=load(p); x=r.get("remote") or {}
    if x.get("item_count") != 0 or x.get("numbered_item_count") != 0: raise RuntimeError(f"remote not empty: {x}")
    print("EMPTY_REMOTE_OK")
def after(p):
    r=load(p); x=r.get("remote") or {}; d=r.get("differences") or {}
    if x.get("numbered_item_count") != 9: raise RuntimeError(f"expected 9 remote chapters: {x}")
    for k in ("local_only_chapters","remote_only_chapters","title_mismatches","duplicate_remote_chapter_numbers","position_mismatches"):
        if d.get(k): raise RuntimeError(f"reconcile mismatch {k}: {d.get(k)}")
    nums=sorted(row.get("chapter") for row in r.get("scheduled",[]) if isinstance(row.get("chapter"),int))
    if nums != list(range(1,10)): raise RuntimeError(f"expected scheduled 1-9: {nums}")
    print("POST_CREATE_OK")
def classify(code):
    one=load(S/"one-shot.json"); res=one.get("result") or {}
    if code==0 and res.get("platform_status")=="success": print("success"); return
    msg=str(res.get("message") or "")
    if re.search(r"(每日|当日|今日|本日|单日|今天|每月|本月|单月|月度)[^，。;；]{0,16}上限",msg): print("daily_limit"); return
    raise RuntimeError(f"publish-now non-limit failure: code={code}, message={msg!r}")
def final(p,result):
    r=load(p); rows=[x for x in r.get("remote_items",[]) if isinstance(x.get("chapter_number"),int)]
    if sorted(x["chapter_number"] for x in rows) != list(range(1,10)): raise RuntimeError("unexpected final remote set")
    bad=[(x["chapter_number"],x.get("status")) for x in rows if x.get("status") not in {"published","scheduled"}]
    if bad: raise RuntimeError(f"unexpected statuses {bad}")
    pub=sorted(x["chapter_number"] for x in rows if x.get("status")=="published"); sch=sorted(x["chapter_number"] for x in rows if x.get("status")=="scheduled")
    if result=="success" and sch: raise RuntimeError(f"publisher said success but still scheduled {sch}")
    if result=="daily_limit" and not sch: result="success"
    done=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out={"version":1,"book_title":TITLE,"completed_at":done,"requested_chapters":list(range(1,10)),"published_chapters":pub,"still_scheduled_chapters":sch,"publish_result":result,"verified_by_read_only_reconcile":True}
    (S/"launch-result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    one=load(S/"one-shot.json"); one.update({"status":"completed","completed_at":done,"result":{"platform_status":"published" if not sch else "partial_daily_limit","published_chapters":pub,"still_scheduled_chapters":sch}}); (S/"one-shot.json").write_text(json.dumps(one,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False))

ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
for n in ("before","after"): q=sp.add_parser(n); q.add_argument("report")
q=sp.add_parser("classify"); q.add_argument("code",type=int)
q=sp.add_parser("final"); q.add_argument("report"); q.add_argument("result",choices=("success","daily_limit"))
a=ap.parse_args()
try:
    {"before":lambda:before(a.report),"after":lambda:after(a.report),"classify":lambda:classify(a.code),"final":lambda:final(a.report,a.result)}[a.cmd]()
except Exception as e: print(f"ERROR: {e}"); raise SystemExit(2)
