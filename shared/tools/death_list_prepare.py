#!/usr/bin/env python3
import json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

D = Path("novels/death-list"); S = D / "platform-sync"; TZ = ZoneInfo("Asia/Shanghai")

def verify():
    counts = {}
    for n in range(1,10):
        p = D / "chapters" / f"chapter-{n:03d}.md"
        if not p.is_file(): raise RuntimeError(f"missing {p}")
        lines = p.read_text(encoding="utf-8").splitlines()
        if not lines or not re.match(rf"^#\s*第\s*{n}\s*章\s*\S", lines[0].strip()): raise RuntimeError(f"bad heading {p}")
        counts[n] = len(re.sub(r"\s", "", "\n".join(lines[1:])))
    total = sum(counts.values())
    if any(v < 2000 for v in counts.values()) or not 19000 <= total <= 20500: raise RuntimeError(f"invalid launch counts {counts}, total={total}")
    print("chapter_chars=" + ",".join(f"{n}:{counts[n]}" for n in counts)); print(f"launch_total_chars={total}")

def write(name, data): (S/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def prepare():
    verify(); book_id=(S/".discovered-book-id").read_text(encoding="utf-8").strip()
    if not book_id.isdigit(): raise RuntimeError("invalid discovered book id")
    now=datetime.now(TZ).replace(microsecond=0); start=(now.date()+timedelta(days=1)).isoformat()
    config={"version":1,"platform":"fanqie","book_id":book_id,"novel_slug":"death-list","chapter_glob":"chapters/chapter-*.md","sync_enabled":True,"browser":{"headless":True},"safety":{"require_explicit_authorization":True,"require_audit_passed":True,"stop_on_create_failure":True,"max_mutations_per_run":20}}
    policy={"version":1,"book_id":book_id,"policy_status":"active","timezone":"Asia/Shanghai","declaration":{"use_ai":True},"chapter_length":{"hard_minimum_chars":2000,"preferred_target_chars":"scene-complete; about 2000-2600 for launch","counting_basis":"body_non_whitespace_characters"},"schedule":{"mode":"fixed_start","chapters_per_day":9,"slots":["00:00"],"start_date":None,"group_size":9,"same_timestamp_within_group":True,"require_complete_groups":True,"daily_word_floor":{"enabled":True,"minimum_chars_exclusive":18999,"normal_chapters":9,"preserve_order":True,"same_timestamp":True,"notes":"Approximate 20k launch allowance; Fanqie real limit response is authoritative."}},"notes":"Never pad scenes for quota; stop on the first real daily/monthly limit response."}
    queue={"version":1,"book_id":book_id,"updated_at":now.astimezone(timezone.utc).isoformat(),"operations":[{"id":"death-list-create-001-009-20260906","action":"create","chapters":"1-9","schedule_mode":"fixed_start","start_date":start,"authorized":True,"status":"pending","audit":{"status":"passed","basis":"Author authorized audited chapters 1-9. Local quality/length gates pass; exact-title lookup and an empty remote reconcile are required before create."}}]}
    state={"version":1,"book_id":book_id,"last_sync_at":None,"chapters":{}}
    shot={"version":1,"book_id":book_id,"id":"death-list-publish-now-001-009-20260906","action":"publish_now","chapters":list(range(1,10)),"status":"pending","authorized":True,"triggered_at":now.isoformat(),"audit":{"status":"passed","basis":"Author requested publishing the audited launch batch today up to the real Fanqie limit after exact post-create reconciliation."},"reason":"Publish chapters 1-9 in order; stop on the first real daily/monthly limit response."}
    S.mkdir(parents=True,exist_ok=True)
    for name,data in [("config.json",config),("policy.json",policy),("queue.json",queue),("sync-state.json",state),("one-shot.json",shot)]: write(name,data)
    print(f"PREPARED start={start}")

if __name__ == "__main__":
    try: prepare()
    except Exception as e: print(f"ERROR: {e}"); raise SystemExit(2)
