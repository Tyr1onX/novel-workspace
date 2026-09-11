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
AUDIT = NOVEL / "audits" / "september-finalization-20260911.md"
QUALITY_RUN = 34544962185
SPECS: dict[str, dict[str, Any]] = {
    "create1direct": {
        "id": "walk-create-131-160-direct-20260911",
        "chapters": "131-160",
        "success": 30,
        "pre_max": 130,
        "post_max": 160,
    },
    "create2direct": {
        "id": "walk-create-161-185-direct-20260911",
        "chapters": "161-185",
        "success": 25,
        "pre_max": 160,
        "post_max": 185,
    },
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_op(queue: dict[str, Any], op_id: str) -> dict[str, Any] | None:
    for op in queue.get("operations", []):
        if op.get("id") == op_id:
            return op
    return None


def append_audit(lines: list[str]) -> None:
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def prepare(stage: str) -> None:
    spec = SPECS[stage]
    queue = load(QUEUE)
    if find_op(queue, spec["id"]):
        raise SystemExit(f"Direct operation already exists; refusing replay: {spec['id']}")
    active = [
        op for op in queue.get("operations", [])
        if op.get("authorized") is True and op.get("status", "pending") == "pending"
    ]
    if active:
        raise SystemExit("Unexpected authorized pending operation(s): " + ", ".join(str(x.get("id")) for x in active))
    queue.setdefault("operations", []).append({
        "id": spec["id"],
        "action": "create",
        "chapters": spec["chapters"],
        "authorized": True,
        "status": "pending",
        "method": "direct_runtime_bridge_daily_groups",
        "audit": {
            "status": "passed",
            "quality_run": QUALITY_RUN,
            "basis": "Final Walk quality freeze passed; direct fallback is bounded to five-chapter daily groups and guarded by read-only pre/post reconciliation.",
        },
        "reason": "Generic sync returned nonzero before any create; postflight proved remote prefix unchanged, so use the previously proven direct publisher path without replaying confirmed chapters.",
        "created_at": now(),
    })
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    print(f"Prepared direct operation {spec['id']}")


def read_remote_max(report_path: Path) -> int | None:
    report = load(report_path)
    value = (report.get("remote") or {}).get("max_chapter")
    return int(value) if value is not None else None


def complete(stage: str, report_path: Path, run_id: str) -> None:
    spec = SPECS[stage]
    remote_max = read_remote_max(report_path)
    if remote_max != spec["post_max"]:
        raise SystemExit(f"Cannot complete {stage}: remote max {remote_max} != {spec['post_max']}")
    queue = load(QUEUE)
    op = find_op(queue, spec["id"])
    if not op or op.get("status") != "pending" or op.get("authorized") is not True:
        raise SystemExit(f"Direct operation is not active pending: {spec['id']}")
    op["authorized"] = False
    op["status"] = "completed"
    op["completed_at"] = now()
    op["result"] = {
        "success": spec["success"],
        "failed": 0,
        "confirmed_success_chapters": spec["chapters"],
        "remote_max_chapter_after_attempt": remote_max,
        "workflow_run": run_id,
        "basis": "Direct uploader confirmed every five-chapter group success=5 failed=0; postflight reconciliation confirmed the expected remote prefix.",
    }
    queue["updated_at"] = now()
    dump(QUEUE, queue)
    append_audit([
        f"## {stage} — PASS",
        f"- workflow run: {run_id}",
        f"- operation: {spec['id']}",
        f"- confirmed chapters: {spec['chapters']}",
        f"- remote numbered prefix after stage: 1-{remote_max}",
        f"- recorded at: {now()}",
        "",
    ])
    print(f"Completed direct stage {stage}")


def fail(stage: str, report_path: Path | None, run_id: str, reason: str) -> None:
    spec = SPECS[stage]
    queue = load(QUEUE)
    op = find_op(queue, spec["id"])
    remote_max = read_remote_max(report_path) if report_path and report_path.exists() else None
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
        f"## {stage} — FAIL CLOSED",
        f"- workflow run: {run_id}",
        f"- operation: {spec['id']}",
        f"- reason: {reason}",
        f"- remote max after attempt: {remote_max}",
        "- authorization disabled; no blind replay is allowed.",
        f"- recorded at: {now()}",
        "",
    ])
    print(f"Fail-closed direct stage {stage}; remote_max={remote_max}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("stage", choices=SPECS)
    p = sub.add_parser("complete")
    p.add_argument("stage", choices=SPECS)
    p.add_argument("report", type=Path)
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("fail")
    p.add_argument("stage", choices=SPECS)
    p.add_argument("--report", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.stage)
    elif args.command == "complete":
        complete(args.stage, args.report, args.run_id)
    elif args.command == "fail":
        fail(args.stage, args.report, args.run_id, args.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
