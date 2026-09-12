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
AUDIT = NOVEL / "audits" / "chapters-136-140-quality-pass-20260912.md"
BOOK_ID = "7677956141673892926"
OP_ID = "walk-create-136-140-audited-retry1-20260913"
QUALITY_RUN = 34672766220
CHAPTERS = "136-140"
PRE_MAX = 135
POST_MAX = 140


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_op(queue: dict[str, Any]) -> dict[str, Any] | None:
    for op in queue.get("operations", []):
        if op.get("id") == OP_ID:
            return op
    return None


def append_audit(lines: list[str]) -> None:
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")


def expected_schedule(chapter: int) -> str:
    base = dt.date(2026, 9, 16)
    day = base + dt.timedelta(days=(chapter - 111) // 5)
    return f"{day.isoformat()}T00:00+08:00"


def prepare() -> None:
    if not AUDIT.exists():
        raise SystemExit("Exact quality PASS audit is missing")
    audit_text = AUDIT.read_text(encoding="utf-8")
    required = [
        "Chapters 136–140 quality audit — PASS",
        f"GitHub Actions run: `{QUALITY_RUN}`",
        "QUALITY APPROVED FOR A SINGLE EXACT-RANGE PUBLISH ATTEMPT ONLY",
        "Safe retry authorization basis",
    ]
    for token in required:
        if token not in audit_text:
            raise SystemExit(f"Exact quality audit missing approval token: {token}")

    queue = load(QUEUE)
    if find_op(queue):
        raise SystemExit(f"Exact retry operation already exists; refusing replay: {OP_ID}")
    active = [
        op for op in queue.get("operations", [])
        if op.get("authorized") is True and op.get("status", "pending") == "pending"
    ]
    if active:
        raise SystemExit(
            "Unexpected authorized pending operation(s): "
            + ", ".join(str(op.get("id")) for op in active)
        )

    queue.setdefault("operations", []).append({
        "id": OP_ID,
        "action": "create",
        "chapters": CHAPTERS,
        "schedule_mode": "fixed_start",
        "start_date": "2026-09-21",
        "authorized": True,
        "status": "pending",
        "method": "exact_direct_runtime_bridge_single_five_chapter_group_retry_after_ci_only_failure",
        "audit": {
            "status": "passed",
            "quality_run": QUALITY_RUN,
            "file": "novels/walk-to-earn/audits/chapters-136-140-quality-pass-20260912.md",
            "basis": "Exact automated gate and manual cold-read audit passed; previous exact workflow failed before runtime/preflight/upload and performed no platform mutation.",
        },
        "reason": "Publish only the audited 2026-09-21 five-chapter group after platform prefix 1-135 is independently confirmed; preserve the earlier CI-only failed operation as history.",
        "created_at": now(),
    })
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    print(f"Prepared exact authorized operation: {OP_ID}")


def validate_report(phase: str, report_path: Path) -> None:
    report = load(report_path)
    expected_max = PRE_MAX if phase == "pre" else POST_MAX
    if str(report.get("book_id")) != BOOK_ID:
        raise SystemExit(f"book_id mismatch: {report.get('book_id')}")

    local = report.get("local") or {}
    remote = report.get("remote") or {}
    diff = report.get("differences") or {}

    if local.get("chapter_count") != 185 or local.get("min_chapter") != 1 or local.get("max_chapter") != 185:
        raise SystemExit(f"Unexpected local chapter inventory: {local}")
    if remote.get("numbered_item_count") != expected_max:
        raise SystemExit(f"Remote numbered count {remote.get('numbered_item_count')} != {expected_max}")
    if remote.get("min_chapter") != 1 or remote.get("max_chapter") != expected_max:
        raise SystemExit(f"Unexpected remote prefix: {remote}")
    if diff.get("remote_only_chapters"):
        raise SystemExit(f"Remote-only chapters found: {diff['remote_only_chapters']}")
    if diff.get("duplicate_remote_chapter_numbers"):
        raise SystemExit(f"Duplicate remote chapter numbers: {diff['duplicate_remote_chapter_numbers']}")

    expected_local_only = list(range(expected_max + 1, 186))
    actual_local_only = list(diff.get("local_only_chapters") or [])
    if actual_local_only != expected_local_only:
        raise SystemExit(
            f"Unexpected local-only set: {actual_local_only}; expected {expected_local_only}"
        )

    unexpected_positions = [
        row for row in (diff.get("position_mismatches") or [])
        if int(row.get("chapter") or -1) not in {23, 24}
    ]
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
            raise SystemExit(
                f"Chapter {n} schedule mismatch: {row.get('scheduled_at')} != {expected_at}"
            )

    print(f"Exact reconciliation PASS phase={phase} remote=1-{expected_max}")


def read_remote_max(report_path: Path | None) -> int | None:
    if report_path is None or not report_path.exists():
        return None
    report = load(report_path)
    value = (report.get("remote") or {}).get("max_chapter")
    return int(value) if value is not None else None


def complete(report_path: Path, run_id: str) -> None:
    validate_report("post", report_path)
    queue = load(QUEUE)
    op = find_op(queue)
    if not op or op.get("status") != "pending" or op.get("authorized") is not True:
        raise SystemExit(f"Exact retry operation is not active pending: {OP_ID}")

    op["authorized"] = False
    op["status"] = "completed"
    op["completed_at"] = now()
    op["result"] = {
        "success": 5,
        "failed": 0,
        "confirmed_success_chapters": CHAPTERS,
        "remote_max_chapter_after_attempt": POST_MAX,
        "workflow_run": run_id,
        "basis": "Direct publisher reported success=5 failed=0 and read-only postflight confirmed remote prefix 1-140 with the expected schedule.",
    }
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    append_audit([
        "## Platform publication retry — PASS",
        f"- workflow run: `{run_id}`",
        f"- operation: `{OP_ID}`",
        "- confirmed platform chapters: 136–140",
        "- scheduled together: 2026-09-21 00:00 Asia/Shanghai",
        "- postflight numbered prefix: 1–140",
        f"- recorded at: {now()}",
    ])
    print(f"Completed exact retry operation: {OP_ID}")


def fail(report_path: Path | None, run_id: str, reason: str) -> None:
    queue = load(QUEUE)
    op = find_op(queue)
    remote_max = read_remote_max(report_path)
    if op:
        op["authorized"] = False
        if op.get("status") == "pending":
            op["status"] = "platform_failed"
        op["attempted_at"] = now()
        op["result"] = {
            "workflow_run": run_id,
            "reason": reason,
            "remote_max_chapter_after_attempt": remote_max,
        }
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    append_audit([
        "## Platform publication retry — FAIL CLOSED",
        f"- workflow run: `{run_id}`",
        f"- operation: `{OP_ID}`",
        f"- reason: {reason}",
        f"- remote max after attempt: {remote_max}",
        "- authorization disabled; blind replay is forbidden.",
        f"- recorded at: {now()}",
    ])
    print(f"Fail-closed exact retry operation: {OP_ID}; remote_max={remote_max}")


def main() -> int:
    parser = argparse.ArgumentParser()
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

    if args.command == "prepare":
        prepare()
    elif args.command == "assert-report":
        validate_report(args.phase, args.report)
    elif args.command == "complete":
        complete(args.report, args.run_id)
    elif args.command == "fail":
        fail(args.report, args.run_id, args.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
