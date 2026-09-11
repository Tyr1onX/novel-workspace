#!/usr/bin/env python3
"""Fail-closed controller for the final audited Walk to Earn September sync.

This helper never talks to Fanqie directly. It only:
- normalizes stale local queue ledgers from already verified platform runs;
- creates exactly one authorized operation for the requested stage;
- validates read-only reconciliation reports before/after platform mutation;
- records success/failure audit state so a failed run cannot retry blindly.

Platform mutation remains owned by shared/tools/fanqie_compat.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
NOVEL = ROOT / "novels" / "walk-to-earn"
QUEUE = NOVEL / "platform-sync" / "queue.json"
CONFIG = NOVEL / "platform-sync" / "config.json"
POLICY = NOVEL / "platform-sync" / "policy.json"
AUDIT = NOVEL / "audits" / "september-finalization-20260911.md"
QUALITY_RUN = "34544962185"

STAGES: dict[str, dict[str, Any]] = {
    "refresh": {
        "id": "walk-refresh-111-130-audited-20260911",
        "action": "update",
        "chapters": "111-130",
        "pre_max": 130,
        "post_max": 130,
    },
    "create1": {
        "id": "walk-create-131-160-audited-20260911",
        "action": "create",
        "chapters": "131-160",
        "start_date": "2026-09-20",
        "schedule_mode": "fixed_start",
        "pre_max": 130,
        "post_max": 160,
    },
    "create2": {
        "id": "walk-create-161-185-audited-20260911",
        "action": "create",
        "chapters": "161-185",
        "start_date": "2026-09-26",
        "schedule_mode": "fixed_start",
        "pre_max": 160,
        "post_max": 185,
    },
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def find_op(queue: dict[str, Any], op_id: str) -> dict[str, Any] | None:
    for op in queue.get("operations", []):
        if op.get("id") == op_id:
            return op
    return None


def normalize_verified_history(queue: dict[str, Any]) -> None:
    """Normalize only the stale September operations proven by prior platform logs."""
    op = find_op(queue, "walk-recover-114-115-fill-20260916-20260910")
    if op and op.get("status") == "pending":
        op["authorized"] = False
        op["status"] = "completed"
        op["completed_at"] = "2026-09-10T00:00:00+00:00"
        op["result"] = {
            "success": 2,
            "failed": 0,
            "confirmed_success_chapters": "114-115",
            "basis": "Confirmed by the direct recovery platform logs before the quality freeze.",
        }

    op = find_op(queue, "walk-recover-116-185-schedule-through-20260930-20260910")
    if op and op.get("status") == "pending":
        op["authorized"] = False
        op["status"] = "partial_failed"
        op["attempted_at"] = "2026-09-10T00:00:00+00:00"
        op["result"] = {
            "success": 15,
            "failed": 55,
            "confirmed_success_chapters": "116-130",
            "failed_or_unprocessed_chapters": "131-185",
            "basis": "Recovery logs confirmed 116-130 before chapter 131 stopped; later chapters were not processed.",
        }


def assert_policy() -> None:
    cfg = load(CONFIG)
    pol = load(POLICY)
    safety = cfg.get("safety") or {}
    schedule = pol.get("schedule") or {}
    floor = schedule.get("daily_word_floor") or {}
    expected = {
        "sync_enabled": True,
        "max_mutations_per_run": 30,
        "chapters_per_day": 5,
        "group_size": 5,
        "same_timestamp_within_group": True,
        "require_complete_groups": True,
        "minimum_chars_exclusive": 9999,
        "normal_chapters": 5,
    }
    actual = {
        "sync_enabled": cfg.get("sync_enabled"),
        "max_mutations_per_run": safety.get("max_mutations_per_run"),
        "chapters_per_day": schedule.get("chapters_per_day"),
        "group_size": schedule.get("group_size"),
        "same_timestamp_within_group": schedule.get("same_timestamp_within_group"),
        "require_complete_groups": schedule.get("require_complete_groups"),
        "minimum_chars_exclusive": floor.get("minimum_chars_exclusive"),
        "normal_chapters": floor.get("normal_chapters"),
    }
    if actual != expected:
        raise SystemExit(f"Walk policy/config drifted: {actual!r} != {expected!r}")
    if schedule.get("slots") != ["00:00"] or pol.get("timezone") != "Asia/Shanghai":
        raise SystemExit("Walk schedule slot/timezone drifted")


def operation_payload(stage: str) -> dict[str, Any]:
    spec = STAGES[stage]
    op: dict[str, Any] = {
        "id": spec["id"],
        "action": spec["action"],
        "chapters": spec["chapters"],
        "authorized": True,
        "status": "pending",
        "audit": {
            "status": "passed",
            "quality_run": int(QUALITY_RUN),
            "basis": (
                "Author explicitly requested completion after the quality freeze. "
                f"Walk quality run {QUALITY_RUN} passed template, protected-fact, full novel_gate, "
                "per-chapter >=2000, and strict five-chapter >9999 release-floor checks."
            ),
        },
        "reason": "Finalize the audited September schedule without retrying already confirmed creates.",
    }
    if spec["action"] == "create":
        op["schedule_mode"] = spec["schedule_mode"]
        op["start_date"] = spec["start_date"]
    return op


def prepare(stage: str) -> None:
    assert_policy()
    queue = load(QUEUE)
    normalize_verified_history(queue)
    target_id = STAGES[stage]["id"]
    existing = find_op(queue, target_id)
    if existing:
        raise SystemExit(f"Target operation already exists; refusing replay: {target_id} status={existing.get('status')}")
    active = [
        op for op in queue.get("operations", [])
        if op.get("status", "pending") == "pending" and op.get("authorized") is True
    ]
    if active:
        raise SystemExit("Unexpected authorized pending operation(s): " + ", ".join(str(x.get("id")) for x in active))
    queue.setdefault("operations", []).append(operation_payload(stage))
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    print(f"Prepared exactly one authorized operation: {target_id}")


def expected_schedule(chapter: int) -> str:
    base = dt.date(2026, 9, 16)
    day = base + dt.timedelta(days=(chapter - 111) // 5)
    return f"{day.isoformat()}T00:00+08:00"


def validate_report(stage: str, phase: str, path: Path) -> None:
    report = load(path)
    spec = STAGES[stage]
    remote_max = int(spec[f"{phase}_max"])
    if str(report.get("book_id")) != "7677956141673892926":
        raise SystemExit("Reconcile book_id mismatch")
    local = report.get("local") or {}
    remote = report.get("remote") or {}
    diff = report.get("differences") or {}
    if local.get("chapter_count") != 185 or local.get("min_chapter") != 1 or local.get("max_chapter") != 185:
        raise SystemExit(f"Unexpected local chapter set: {local}")
    if remote.get("numbered_item_count") != remote_max or remote.get("min_chapter") != 1 or remote.get("max_chapter") != remote_max:
        raise SystemExit(f"Unexpected remote prefix for {stage}/{phase}: {remote}")
    if diff.get("remote_only_chapters"):
        raise SystemExit(f"Remote-only chapters detected: {diff['remote_only_chapters']}")
    if diff.get("duplicate_remote_chapter_numbers"):
        raise SystemExit(f"Duplicate remote chapter numbers: {diff['duplicate_remote_chapter_numbers']}")
    expected_local_only = list(range(remote_max + 1, 186))
    actual_local_only = list(diff.get("local_only_chapters") or [])
    if actual_local_only != expected_local_only:
        raise SystemExit(f"Unexpected local-only set: {actual_local_only}, expected {expected_local_only}")

    bad_positions = [
        row for row in (diff.get("position_mismatches") or [])
        if int(row.get("chapter") or -1) not in {23, 24}
    ]
    if bad_positions:
        raise SystemExit(f"Unexpected position mismatch(es): {bad_positions}")

    mismatches = list(diff.get("title_mismatches") or [])
    if stage == "refresh" and phase == "pre":
        outside = [m for m in mismatches if not 111 <= int(m.get("chapter") or -1) <= 130]
        if outside:
            raise SystemExit(f"Unexpected pre-refresh title mismatch(es): {outside}")
    elif mismatches:
        raise SystemExit(f"Title mismatch(es) remain: {mismatches}")

    by_num: dict[int, dict[str, Any]] = {}
    for row in report.get("remote_items") or []:
        n = row.get("chapter_number")
        if isinstance(n, int):
            by_num[n] = row
    for n in range(111, remote_max + 1):
        row = by_num.get(n)
        if row is None:
            raise SystemExit(f"Chapter {n} missing from remote_items")
        if row.get("status") not in {"scheduled", "reviewing"}:
            raise SystemExit(f"Chapter {n} unexpected status: {row.get('status')}")
        exp = expected_schedule(n)
        if row.get("scheduled_at") != exp:
            raise SystemExit(f"Chapter {n} schedule mismatch: {row.get('scheduled_at')} != {exp}")
    print(f"Reconcile assertion PASS: stage={stage} phase={phase} remote=1-{remote_max}")


def audit_append(lines: list[str]) -> None:
    if not AUDIT.exists():
        AUDIT.write_text(
            "# Walk to Earn September finalization audit\n\n"
            "Final quality gate: GitHub Actions run 34544962185 (PASS).\n"
            "Policy: 5 chapters/day, 00:00 Asia/Shanghai, >=2000 each, five-chapter total >9999.\n\n",
            encoding="utf-8",
        )
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def record_success(stage: str, report_path: Path, run_id: str) -> None:
    queue = load(QUEUE)
    op = find_op(queue, STAGES[stage]["id"])
    if not op or op.get("status") != "completed":
        raise SystemExit(f"Sync did not record completed target operation for {stage}")
    report = load(report_path)
    remote = report.get("remote") or {}
    audit_append([
        f"## {stage} — PASS",
        f"- workflow run: {run_id}",
        f"- operation: {STAGES[stage]['id']}",
        f"- remote numbered prefix after stage: 1-{remote.get('max_chapter')}",
        f"- recorded at: {now()}",
        "",
    ])
    print(f"Recorded successful finalization stage: {stage}")


def fail_close(stage: str, report_path: Path | None, run_id: str, reason: str) -> None:
    queue = load(QUEUE)
    op = find_op(queue, STAGES[stage]["id"])
    if op:
        op["authorized"] = False
        if op.get("status") == "pending":
            op["status"] = "platform_failed"
        op["attempted_at"] = now()
        result: dict[str, Any] = {"workflow_run": run_id, "reason": reason}
        if report_path and report_path.exists():
            report = load(report_path)
            result["remote_max_chapter_after_attempt"] = (report.get("remote") or {}).get("max_chapter")
            result["local_only_chapters_after_attempt"] = (report.get("differences") or {}).get("local_only_chapters")
        op["result"] = result
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    audit_append([
        f"## {stage} — FAIL CLOSED",
        f"- workflow run: {run_id}",
        f"- operation: {STAGES[stage]['id']}",
        f"- reason: {reason}",
        "- authorization disabled; no blind retry is permitted.",
        f"- recorded at: {now()}",
        "",
    ])
    print(f"Fail-closed stage {stage}; authorization disabled")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("stage", choices=STAGES)
    p = sub.add_parser("assert-report")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("phase", choices=["pre", "post"])
    p.add_argument("report", type=Path)
    p = sub.add_parser("record-success")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("report", type=Path)
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("fail-close")
    p.add_argument("stage", choices=STAGES)
    p.add_argument("--report", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.stage)
    elif args.command == "assert-report":
        validate_report(args.stage, args.phase, args.report)
    elif args.command == "record-success":
        record_success(args.stage, args.report, args.run_id)
    elif args.command == "fail-close":
        fail_close(args.stage, args.report, args.run_id, args.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
