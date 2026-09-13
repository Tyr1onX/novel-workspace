# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NOVEL = ROOT / "novels" / "walk-to-earn"
QUEUE = NOVEL / "platform-sync" / "queue.json"
AUDIT = NOVEL / "audits" / "chapters-146-185-quality-pass-20260913.md"
BOOK_ID = "7677956141673892926"
QUALITY_RUN = 34763186055

STAGES = {
    "tail1": {
        "op_id": "walk-create-146-160-audited-20260913",
        "chapters": "146-160",
        "pre_max": 145,
        "post_max": 160,
        "start_date": "2026-09-23",
        "success": 15,
    },
    "tail1retry1": {
        "op_id": "walk-create-146-160-audited-retry1-20260914",
        "chapters": "146-160",
        "pre_max": 145,
        "post_max": 160,
        "start_date": "2026-09-23",
        "success": 15,
    },
    "tail1retry2": {
        "op_id": "walk-create-146-160-audited-retry2-20260914",
        "chapters": "146-160",
        "pre_max": 145,
        "post_max": 160,
        "start_date": "2026-09-23",
        "success": 15,
    },
    "tail2": {
        "op_id": "walk-create-161-185-audited-20260913",
        "chapters": "161-185",
        "pre_max": 160,
        "post_max": 185,
        "start_date": "2026-09-26",
        "success": 25,
    },
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cfg(stage: str) -> dict[str, Any]:
    return STAGES[stage]


def find_op(queue: dict[str, Any], stage: str) -> dict[str, Any] | None:
    op_id = cfg(stage)["op_id"]
    return next((op for op in queue.get("operations", []) if op.get("id") == op_id), None)


def append_audit(lines: list[str]) -> None:
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")


def expected_schedule(chapter: int) -> str:
    base = dt.date(2026, 9, 16)
    day = base + dt.timedelta(days=(chapter - 111) // 5)
    return f"{day.isoformat()}T00:00+08:00"


def assert_approval() -> None:
    if not AUDIT.exists():
        raise SystemExit("Tail quality approval audit is missing")
    text = AUDIT.read_text(encoding="utf-8")
    required = [
        "Walk to Earn chapters 146–185 quality approval — 2026-09-13",
        f"GitHub Actions run: `{QUALITY_RUN}`",
        "QUALITY APPROVED FOR STAGED EXACT-RANGE PUBLICATION ONLY",
    ]
    for token in required:
        if token not in text:
            raise SystemExit(f"Tail quality audit missing approval token: {token}")


def prepare(stage: str) -> None:
    assert_approval()
    c = cfg(stage)
    queue = load(QUEUE)
    if find_op(queue, stage):
        raise SystemExit(f"Exact operation already exists; refusing replay: {c['op_id']}")
    active = [op for op in queue.get("operations", []) if op.get("authorized") is True and op.get("status", "pending") == "pending"]
    if active:
        raise SystemExit("Unexpected authorized pending operation(s): " + ", ".join(str(op.get("id")) for op in active))
    queue.setdefault("operations", []).append({
        "id": c["op_id"],
        "action": "create",
        "chapters": c["chapters"],
        "schedule_mode": "fixed_start",
        "start_date": c["start_date"],
        "authorized": True,
        "status": "pending",
        "method": "exact_direct_runtime_bridge_five_chapter_groups",
        "audit": {
            "status": "passed",
            "quality_run": QUALITY_RUN,
            "file": "novels/walk-to-earn/audits/chapters-146-185-quality-pass-20260913.md",
            "basis": "Full tail automatic gate and chapter-by-chapter manual cold-read audit passed after final corrections.",
        },
        "reason": f"Publish only audited chapters {c['chapters']} after exact remote-prefix proof; stop on first failed five-chapter group.",
        "created_at": now(),
    })
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    print(f"Prepared exact authorized operation: {c['op_id']}")


def validate_report(stage: str, phase: str, report_path: Path) -> None:
    c = cfg(stage)
    report = load(report_path)
    expected_max = c["pre_max"] if phase == "pre" else c["post_max"]
    if str(report.get("book_id")) != BOOK_ID:
        raise SystemExit(f"book_id mismatch: {report.get('book_id')}")
    local = report.get("local") or {}
    remote = report.get("remote") or {}
    diff = report.get("differences") or {}
    if local.get("chapter_count") != 185 or local.get("min_chapter") != 1 or local.get("max_chapter") != 185:
        raise SystemExit(f"Unexpected local chapter inventory: {local}")
    if remote.get("numbered_item_count") != expected_max or remote.get("min_chapter") != 1 or remote.get("max_chapter") != expected_max:
        raise SystemExit(f"Unexpected remote prefix: {remote}; expected 1-{expected_max}")
    if diff.get("remote_only_chapters"):
        raise SystemExit(f"Remote-only chapters found: {diff['remote_only_chapters']}")
    if diff.get("duplicate_remote_chapter_numbers"):
        raise SystemExit(f"Duplicate remote chapter numbers: {diff['duplicate_remote_chapter_numbers']}")
    expected_local_only = list(range(expected_max + 1, 186))
    actual_local_only = list(diff.get("local_only_chapters") or [])
    if actual_local_only != expected_local_only:
        raise SystemExit(f"Unexpected local-only set: {actual_local_only}; expected {expected_local_only}")
    unexpected_positions = [row for row in (diff.get("position_mismatches") or []) if int(row.get("chapter") or -1) not in {23, 24}]
    if unexpected_positions:
        raise SystemExit(f"Unexpected position mismatch(es): {unexpected_positions}")
    if diff.get("title_mismatches"):
        raise SystemExit(f"Title mismatch(es): {diff['title_mismatches']}")
    by_num: dict[int, dict[str, Any]] = {}
    for row in report.get("remote_items") or []:
        n = row.get("chapter_number")
        if isinstance(n, int):
            by_num[n] = row
    for n in range(111, expected_max + 1):
        row = by_num.get(n)
        if row is None:
            raise SystemExit(f"Remote chapter {n} missing from reconciliation items")
        if row.get("status") not in {"scheduled", "reviewing"}:
            raise SystemExit(f"Chapter {n} unexpected status: {row.get('status')}")
        expected_at = expected_schedule(n)
        if row.get("scheduled_at") != expected_at:
            raise SystemExit(f"Chapter {n} schedule mismatch: {row.get('scheduled_at')} != {expected_at}")
    print(f"Exact reconciliation PASS stage={stage} phase={phase} remote=1-{expected_max}")


def read_remote_max(report_path: Path | None) -> int | None:
    if report_path is None or not report_path.exists():
        return None
    value = (load(report_path).get("remote") or {}).get("max_chapter")
    return int(value) if value is not None else None


def complete(stage: str, report_path: Path, run_id: str) -> None:
    c = cfg(stage)
    validate_report(stage, "post", report_path)
    queue = load(QUEUE)
    op = find_op(queue, stage)
    if not op or op.get("status") != "pending" or op.get("authorized") is not True:
        raise SystemExit(f"Exact operation is not active pending: {c['op_id']}")
    op["authorized"] = False
    op["status"] = "completed"
    op["completed_at"] = now()
    op["result"] = {
        "success": c["success"],
        "failed": 0,
        "confirmed_success_chapters": c["chapters"],
        "remote_max_chapter_after_attempt": c["post_max"],
        "workflow_run": run_id,
        "basis": "Every five-chapter publisher call reported success=5 failed=0 and read-only postflight confirmed the exact expected remote prefix and schedule.",
    }
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    append_audit([
        f"## Platform publication {stage} — PASS",
        f"- workflow run: `{run_id}`",
        f"- operation: `{c['op_id']}`",
        f"- confirmed platform chapters: {c['chapters']}",
        f"- postflight numbered prefix: 1–{c['post_max']}",
        f"- recorded at: {now()}",
    ])
    print(f"Completed exact operation: {c['op_id']}")


def fail(stage: str, report_path: Path | None, run_id: str, reason: str) -> None:
    c = cfg(stage)
    queue = load(QUEUE)
    op = find_op(queue, stage)
    remote_max = read_remote_max(report_path)
    if op:
        op["authorized"] = False
        if op.get("status") == "pending":
            op["status"] = "platform_failed"
        op["attempted_at"] = now()
        op["result"] = {"workflow_run": run_id, "reason": reason, "remote_max_chapter_after_attempt": remote_max}
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    append_audit([
        f"## Platform publication {stage} — FAIL CLOSED",
        f"- workflow run: `{run_id}`",
        f"- operation: `{c['op_id']}`",
        f"- reason: {reason}",
        f"- remote max after attempt: {remote_max}",
        "- authorization disabled; blind replay is forbidden.",
        f"- recorded at: {now()}",
    ])
    print(f"Fail-closed exact operation: {c['op_id']}; remote_max={remote_max}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=sorted(STAGES))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    p = sub.add_parser("assert-report")
    p.add_argument("phase", choices=["pre", "post"])
    p.add_argument("report", type=Path)
    p = sub.add_parser("complete")
    p.add_argument("report", type=Path)
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("fail")
    p.add_argument("--report", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "prepare": prepare(args.stage)
    elif args.command == "assert-report": validate_report(args.stage, args.phase, args.report)
    elif args.command == "complete": complete(args.stage, args.report, args.run_id)
    elif args.command == "fail": fail(args.stage, args.report, args.run_id, args.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
