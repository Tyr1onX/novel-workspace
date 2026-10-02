#!/usr/bin/env python3
"""Repository-driven Fanqie publishing controller.

The repository owns policy, authorization, sync state, and release constraints.
Browser automation is performed by a pinned, locally installed fanqie-publisher
runtime. No platform mutation happens unless an operation is audit-passed,
explicitly authorized, and satisfies the active release policy.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

CHAPTER_FILE_RE = re.compile(r"chapter-(\d+)\.md$", re.I)
CHAPTER_HEADING_RE = re.compile(r"^#\s*第\s*(\d+)\s*章\s*(.*?)\s*$")
RANGE_TOKEN_RE = re.compile(r"^(\d+)(?:-(\d+))?$")
SUMMARY_RE = re.compile(r"成功:\s*(\d+)\s+失败:\s*(\d+)")
EDIT_SUMMARY_RE = re.compile(r"修改完成!\s*成功:\s*(\d+)\s+失败:\s*(\d+)")
RESCHEDULE_SUMMARY_RE = re.compile(r"修改排期完成!\s*成功:\s*(\d+)\s+失败:\s*(\d+)")


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    body: str
    path: Path
    sha256: str
    char_count: int


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SyncError(f"missing required file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SyncError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SyncError(f"expected JSON object in {path}")
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def normalize_body(lines: list[str]) -> str:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def parse_chapter(path: Path) -> Chapter:
    file_match = CHAPTER_FILE_RE.search(path.name)
    if not file_match:
        raise SyncError(f"unsupported chapter filename: {path.name}")
    file_number = int(file_match.group(1))
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    heading_index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if heading_index is None:
        raise SyncError(f"empty chapter: {path}")
    heading = CHAPTER_HEADING_RE.match(lines[heading_index].strip())
    if not heading:
        raise SyncError(f"first non-empty line is not '# 第N章 标题': {path}")
    heading_number = int(heading.group(1))
    if heading_number != file_number:
        raise SyncError(
            f"chapter number mismatch in {path}: filename={file_number}, heading={heading_number}"
        )
    title = heading.group(2).strip()
    if not title:
        raise SyncError(f"empty chapter title: {path}")
    body = normalize_body(lines[heading_index + 1 :])
    if not body.strip():
        raise SyncError(f"empty chapter body: {path}")
    digest = hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()
    char_count = len(re.sub(r"\s", "", body))
    return Chapter(file_number, title, body, path, digest, char_count)


def discover_chapters(novel_dir: Path, chapter_glob: str) -> dict[int, Chapter]:
    found: dict[int, Chapter] = {}
    for path in sorted(novel_dir.glob(chapter_glob)):
        chapter = parse_chapter(path)
        if chapter.number in found:
            raise SyncError(
                f"duplicate chapter number {chapter.number}: {found[chapter.number].path} and {path}"
            )
        found[chapter.number] = chapter
    if not found:
        raise SyncError(f"no chapters found using glob {chapter_glob!r} under {novel_dir}")
    return found


def parse_chapter_spec(value: Any) -> list[int]:
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        out: list[int] = []
        for item in value:
            out.extend(parse_chapter_spec(item))
        return sorted(set(out))
    if not isinstance(value, str):
        raise SyncError(f"invalid chapter selector: {value!r}")
    out: set[int] = set()
    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            continue
        match = RANGE_TOKEN_RE.match(token)
        if not match:
            raise SyncError(f"invalid chapter range token: {token!r}")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if end < start:
            raise SyncError(f"descending chapter range is not allowed: {token!r}")
        out.update(range(start, end + 1))
    if not out:
        raise SyncError("chapter selector resolved to an empty set")
    return sorted(out)


def compact_spec(numbers: Iterable[int]) -> str:
    nums = sorted(set(int(n) for n in numbers))
    if not nums:
        return ""
    parts: list[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    parts.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(parts)


def validate_policy(policy: dict[str, Any], config: dict[str, Any]) -> None:
    if policy.get("version") != 1:
        raise SyncError("policy.json version must be 1")
    schedule = policy.get("schedule") or {}
    if schedule.get("mode") not in {"auto_continue", "fixed_start"}:
        raise SyncError("policy.schedule.mode must be auto_continue or fixed_start")
    slots = schedule.get("slots") or []
    if not slots or not all(isinstance(s, str) and re.match(r"^\d{2}:\d{2}$", s) for s in slots):
        raise SyncError("policy.schedule.slots must contain HH:MM strings")
    per_day = schedule.get("chapters_per_day")
    if not isinstance(per_day, int) or per_day < 1 or per_day > 20:
        raise SyncError("policy.schedule.chapters_per_day must be 1..20")
    group_size = schedule.get("group_size", per_day)
    if not isinstance(group_size, int) or group_size < 1:
        raise SyncError("policy.schedule.group_size must be a positive integer")
    if schedule.get("require_complete_groups") is True and group_size != per_day:
        raise SyncError("require_complete_groups=true requires group_size=chapters_per_day")

    chapter_length = policy.get("chapter_length") or {}
    hard_minimum = chapter_length.get("hard_minimum_chars")
    if hard_minimum is not None and (not isinstance(hard_minimum, int) or hard_minimum < 1):
        raise SyncError("policy.chapter_length.hard_minimum_chars must be a positive integer")

    floor = schedule.get("daily_word_floor") or {}
    if floor.get("enabled") is True:
        minimum = floor.get("minimum_chars_exclusive", floor.get("minimum_chars"))
        if not isinstance(minimum, int) or minimum < 0:
            raise SyncError("enabled daily_word_floor needs a non-negative integer minimum")
        normal = floor.get("normal_chapters", group_size)
        if not isinstance(normal, int) or normal < 1:
            raise SyncError("daily_word_floor.normal_chapters must be a positive integer")
        if schedule.get("require_complete_groups") is True and normal != group_size:
            raise SyncError("strict release groups require daily_word_floor.normal_chapters=group_size")

    if config.get("book_id") != policy.get("book_id"):
        raise SyncError("book_id differs between config.json and policy.json")
    if config.get("sync_enabled") and policy.get("policy_status") != "active":
        raise SyncError("sync_enabled=true requires policy_status='active'")


def validate_operation(op: dict[str, Any], chapters: dict[int, Chapter]) -> list[int]:
    op_id = op.get("id")
    if not isinstance(op_id, str) or not op_id.strip():
        raise SyncError("each queue operation needs a non-empty id")
    action = op.get("action")
    if action not in {"create", "update", "reschedule_all"}:
        raise SyncError(f"{op_id}: unsupported action {action!r}")
    if action == "reschedule_all":
        nums: list[int] = []
    else:
        nums = parse_chapter_spec(op.get("chapters"))
        missing = [n for n in nums if n not in chapters]
        if missing:
            raise SyncError(f"{op_id}: local chapters missing: {compact_spec(missing)}")
    audit = op.get("audit") or {}
    if op.get("authorized") is True and audit.get("status") != "passed":
        raise SyncError(f"{op_id}: authorized operation must have audit.status='passed'")
    return nums


def _require_consecutive(op_id: str, nums: list[int]) -> None:
    if not nums:
        raise SyncError(f"{op_id}: release group is empty")
    expected = list(range(nums[0], nums[-1] + 1))
    if nums != expected:
        raise SyncError(f"{op_id}: release chapters must be consecutive: {compact_spec(nums)}")


def _validate_release_groups(
    op_id: str,
    nums: list[int],
    chapters: dict[int, Chapter],
    policy: dict[str, Any],
) -> None:
    schedule = policy.get("schedule") or {}
    group_size = int(schedule.get("group_size") or schedule.get("chapters_per_day") or 1)
    _require_consecutive(op_id, nums)
    if len(nums) % group_size != 0:
        raise SyncError(
            f"{op_id}: {len(nums)} chapters leave a partial release day; "
            f"strict group size is {group_size}"
        )

    floor = schedule.get("daily_word_floor") or {}
    if floor.get("enabled") is not True:
        return
    minimum = int(floor.get("minimum_chars_exclusive", floor.get("minimum_chars", 0)))
    for i in range(0, len(nums), group_size):
        group = nums[i : i + group_size]
        total = sum(chapters[n].char_count for n in group)
        if total <= minimum:
            raise SyncError(
                f"{op_id}: chapters {compact_spec(group)} total {total} chars; "
                f"daily release must be > {minimum}"
            )


def validate_release_operation(
    op: dict[str, Any],
    chapters: dict[int, Chapter],
    policy: dict[str, Any],
) -> list[int]:
    """Fail closed on content/schedule constraints before a pending mutation."""
    nums = validate_operation(op, chapters)
    op_id = str(op["id"])
    action = op["action"]

    chapter_length = policy.get("chapter_length") or {}
    hard_minimum = chapter_length.get("hard_minimum_chars")
    if action in {"create", "update"} and isinstance(hard_minimum, int):
        short = [n for n in nums if chapters[n].char_count < hard_minimum]
        if short:
            details = ", ".join(f"{n}={chapters[n].char_count}" for n in short)
            raise SyncError(
                f"{op_id}: chapters below hard body floor {hard_minimum}: {details}"
            )

    schedule = policy.get("schedule") or {}
    strict_groups = schedule.get("require_complete_groups") is True
    if action == "create" and strict_groups:
        mode = op.get("schedule_mode") or schedule.get("mode")
        if mode != "fixed_start":
            raise SyncError(
                f"{op_id}: strict complete release groups require fixed_start; got {mode!r}"
            )
        if not (op.get("start_date") or schedule.get("start_date")):
            raise SyncError(f"{op_id}: strict fixed_start create requires an explicit start_date")
        _validate_release_groups(op_id, nums, chapters, policy)

    if action == "reschedule_all" and strict_groups:
        audit = op.get("audit") or {}
        expected_spec = audit.get("expected_pending_chapters")
        if not expected_spec:
            raise SyncError(
                f"{op_id}: strict reschedule_all requires audit.expected_pending_chapters "
                "from a fresh read-only reconcile"
            )
        expected = parse_chapter_spec(expected_spec)
        missing = [n for n in expected if n not in chapters]
        if missing:
            raise SyncError(f"{op_id}: expected pending chapters missing locally: {compact_spec(missing)}")
        _validate_release_groups(op_id, expected, chapters, policy)

    return nums


def create_execution_numbers(op: dict[str, Any], nums: list[int]) -> list[int]:
    """Filter chapters confirmed by the operation audit as already present remotely."""
    if op.get("action") != "create":
        return nums
    audit = op.get("audit") or {}
    existing_spec = audit.get("already_present_chapters")
    if not existing_spec:
        return nums
    existing = parse_chapter_spec(existing_spec)
    outside = [n for n in existing if n not in nums]
    if outside:
        raise SyncError(
            f"{op['id']}: audit.already_present_chapters outside create selector: "
            f"{compact_spec(outside)}"
        )
    existing_set = set(existing)
    remaining = [n for n in nums if n not in existing_set]
    if not remaining:
        raise SyncError(f"{op['id']}: all selected create chapters are already present remotely")
    return remaining


def get_paths(novel_dir: Path) -> dict[str, Path]:
    sync_dir = novel_dir / "platform-sync"
    return {
        "sync_dir": sync_dir,
        "config": sync_dir / "config.json",
        "policy": sync_dir / "policy.json",
        "queue": sync_dir / "queue.json",
        "state": sync_dir / "sync-state.json",
    }


def load_model(novel_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[int, Chapter]]:
    paths = get_paths(novel_dir)
    config = load_json(paths["config"])
    policy = load_json(paths["policy"])
    queue = load_json(paths["queue"])
    if config.get("version") != 1:
        raise SyncError("config.json version must be 1")
    if queue.get("version") != 1:
        raise SyncError("queue.json version must be 1")
    if queue.get("book_id") != config.get("book_id"):
        raise SyncError("book_id differs between config.json and queue.json")
    validate_policy(policy, config)
    chapters = discover_chapters(novel_dir, config.get("chapter_glob", "chapters/volume-*/chapter-*.md"))
    seen_ids: set[str] = set()
    for op in queue.get("operations", []):
        if not isinstance(op, dict):
            raise SyncError("queue operations must be JSON objects")
        if op.get("id") in seen_ids:
            raise SyncError(f"duplicate queue operation id: {op.get('id')}")
        seen_ids.add(op.get("id"))
        validate_operation(op, chapters)
    return config, policy, queue, chapters


def pending_operations(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        op
        for op in queue.get("operations", [])
        if op.get("status", "pending") == "pending"
        and op.get("authorized") is True
        and (op.get("audit") or {}).get("status") == "passed"
    ]


def build_plan(novel_dir: Path) -> dict[str, Any]:
    config, policy, queue, chapters = load_model(novel_dir)
    ops = []
    for op in pending_operations(queue):
        nums = validate_release_operation(op, chapters, policy)
        entry = {
            "id": op["id"],
            "action": op["action"],
            "chapters": nums,
            "chapter_spec": compact_spec(nums),
        }
        if nums:
            entry["items"] = [
                {
                    "number": n,
                    "title": chapters[n].title,
                    "chars": chapters[n].char_count,
                    "sha256": chapters[n].sha256,
                }
                for n in nums
            ]
        ops.append(entry)
    return {
        "book_id": config["book_id"],
        "enabled": bool(config.get("sync_enabled", False)),
        "schedule": policy["schedule"],
        "pending_operations": ops,
        "pending_count": len(ops),
    }


def resolve_runtime(runtime_arg: str | None) -> Path:
    if runtime_arg:
        runtime = Path(os.path.expandvars(os.path.expanduser(runtime_arg)))
    elif os.environ.get("FANQIE_RUNTIME_DIR"):
        runtime = Path(os.path.expandvars(os.path.expanduser(os.environ["FANQIE_RUNTIME_DIR"])))
    else:
        runtime = Path.home() / ".novel-workspace" / "fanqie-publisher"
    return runtime.resolve()


def runtime_command(runtime: Path, args: list[str]) -> list[str]:
    script = runtime / "fanqie_upload.py"
    if not script.exists():
        raise SyncError(
            f"Fanqie runtime is not installed at {runtime}. Run bootstrap_fanqie_sync_macos.sh once."
        )
    return [sys.executable, str(script), *args]


def run_upstream(command: list[str], *, assume_yes: bool = True) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        input="y\n" if assume_yes else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    output = proc.stdout or ""
    print(output, end="" if output.endswith("\n") else "\n")
    return proc.returncode, output


def parse_success(
    output: str,
    expected: int,
    *,
    edit: bool = False,
    allow_already_present: bool = False,
) -> None:
    regex = EDIT_SUMMARY_RE if edit else SUMMARY_RE
    matches = list(regex.finditer(output))
    if not matches:
        if allow_already_present and "本地章节都已经在平台上了" in output:
            return
        raise SyncError("publisher did not emit a completion summary; operation is not confirmed")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if failed != 0:
        raise SyncError(
            f"publisher reported failures: expected at most {expected}, success={success}, failed={failed}"
        )
    if success == expected:
        return
    if allow_already_present and 0 < success <= expected:
        return
    raise SyncError(
        f"publisher summary mismatch: expected {expected}, success={success}, failed={failed}"
    )


def parse_reschedule_success(output: str) -> None:
    matches = list(RESCHEDULE_SUMMARY_RE.finditer(output))
    if not matches:
        raise SyncError("reschedule operation did not emit a completion summary")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if failed != 0:
        raise SyncError(f"reschedule completed with failures: success={success}, failed={failed}")


def operation_command(
    runtime: Path,
    novel_dir: Path,
    config: dict[str, Any],
    policy: dict[str, Any],
    op: dict[str, Any],
    chapters: dict[int, Chapter],
) -> tuple[list[str], int, bool]:
    book_id = str(config["book_id"])
    headless = bool(config.get("browser", {}).get("headless", True))
    use_ai = bool(policy.get("declaration", {}).get("use_ai", True))
    schedule = policy["schedule"]
    action = op["action"]

    if action in {"create", "update"}:
        nums = validate_release_operation(op, chapters, policy)
        execution_nums = create_execution_numbers(op, nums)
        spec = compact_spec(execution_nums)
        args = ["upload", str((novel_dir / "chapters").resolve()), "--book-id", book_id, "--chapters", spec]
        if action == "update":
            args.append("--edit")
        else:
            mode = op.get("schedule_mode") or schedule.get("mode", "auto_continue")
            if mode == "auto_continue":
                args.extend(["--auto-continue", "--per-day", str(schedule["chapters_per_day"]), "--time", ",".join(schedule["slots"])])
            elif mode == "fixed_start":
                start_date = op.get("start_date") or schedule.get("start_date")
                if not start_date:
                    raise SyncError(f"{op['id']}: fixed_start requires start_date")
                args.extend(["--schedule", start_date, "--per-day", str(schedule["chapters_per_day"]), "--time", ",".join(schedule["slots"])])
            else:
                raise SyncError(f"{op['id']}: unknown schedule mode {mode}")
        if use_ai:
            args.append("--use-ai")
        if headless:
            args.append("--headless")
        return runtime_command(runtime, args), len(execution_nums), action == "update"

    if action == "reschedule_all":
        validate_release_operation(op, chapters, policy)
        start_date = op.get("start_date") or schedule.get("start_date")
        if not start_date:
            raise SyncError(f"{op['id']}: reschedule_all requires explicit start_date")
        args = [
            "reschedule",
            "--book-id",
            book_id,
            "--schedule",
            start_date,
            "--per-day",
            str(schedule["chapters_per_day"]),
            "--time",
            ",".join(schedule["slots"]),
            "--all-volumes",
        ]
        if headless:
            args.append("--headless")
        return runtime_command(runtime, args), -1, False

    raise SyncError(f"unsupported action {action}")


def update_local_state(
    novel_dir: Path,
    queue: dict[str, Any],
    completed: list[tuple[dict[str, Any], list[int]]],
    chapters: dict[int, Chapter],
) -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    completed_ids = {op["id"] for op, _ in completed}
    for op in queue.get("operations", []):
        if op.get("id") in completed_ids:
            op["status"] = "completed"
            op["completed_at"] = now
    queue["updated_at"] = now
    paths = get_paths(novel_dir)
    atomic_write_json(paths["queue"], queue)

    state = load_json(paths["state"])
    state.setdefault("chapters", {})
    for op, nums in completed:
        if op["action"] not in {"create", "update"}:
            continue
        for n in nums:
            ch = chapters[n]
            state["chapters"][str(n)] = {
                "local_sha256": ch.sha256,
                "last_action": op["action"],
                "last_synced_at": now,
                "queue_operation_id": op["id"],
            }
    state["last_sync_at"] = now
    atomic_write_json(paths["state"], state)


def cmd_validate(novel_dir: Path) -> int:
    config, policy, queue, chapters = load_model(novel_dir)
    for op in pending_operations(queue):
        validate_release_operation(op, chapters, policy)
    print(f"OK: {novel_dir}")
    print(f"book_id: {config['book_id']}")
    print(f"chapters: {min(chapters)}-{max(chapters)} ({len(chapters)})")
    print(f"queue operations: {len(queue.get('operations', []))}")
    print(f"authorized pending: {len(pending_operations(queue))}")
    print(f"sync_enabled: {bool(config.get('sync_enabled', False))}")
    return 0


def cmd_plan(novel_dir: Path, as_json: bool) -> int:
    plan = build_plan(novel_dir)
    if as_json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    print(f"book_id: {plan['book_id']}")
    print(f"sync enabled: {plan['enabled']}")
    print(f"pending operations: {plan['pending_count']}")
    for op in plan["pending_operations"]:
        label = op["chapter_spec"] or "all pending remote chapters"
        print(f"- {op['id']}: {op['action']} {label}")
    return 0


def cmd_sync(novel_dir: Path, runtime_arg: str | None, dry_run: bool) -> int:
    config, policy, queue, chapters = load_model(novel_dir)
    ops = pending_operations(queue)
    if not ops:
        print("No authorized pending operations.")
        return 0
    if not config.get("sync_enabled", False):
        print("Sync is disabled in platform-sync/config.json; no platform mutation performed.")
        return 0
    mutation_count = sum(
        len(validate_release_operation(op, chapters, policy))
        for op in ops
        if op.get("action") in {"create", "update"}
    )
    max_mutations = int((config.get("safety") or {}).get("max_mutations_per_run", 30))
    if mutation_count > max_mutations:
        raise SyncError(
            f"authorized mutations ({mutation_count}) exceed max_mutations_per_run ({max_mutations})"
        )
    runtime = resolve_runtime(runtime_arg)
    completed: list[tuple[dict[str, Any], list[int]]] = []
    for op in ops:
        command, expected, is_edit = operation_command(runtime, novel_dir, config, policy, op, chapters)
        print("$ " + subprocess.list2cmdline(command))
        if dry_run:
            continue
        code, output = run_upstream(command, assume_yes=True)
        if code != 0:
            raise SyncError(f"publisher process exited with code {code} for {op['id']}")
        nums = validate_operation(op, chapters)
        nums = create_execution_numbers(op, nums)
        if expected >= 0:
            parse_success(
                output,
                expected,
                edit=is_edit,
                allow_already_present=(op.get("action") == "create"),
            )
        else:
            parse_reschedule_success(output)
        completed.append((op, nums))
    if dry_run:
        print("Dry run only; queue/state unchanged.")
        return 0
    if completed:
        update_local_state(novel_dir, queue, completed, chapters)
        print(f"Recorded {len(completed)} completed operation(s) in queue/state.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository-driven Fanqie sync controller")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "plan", "sync"):
        p = sub.add_parser(name)
        p.add_argument("novel_dir", type=Path)
        if name == "plan":
            p.add_argument("--json", action="store_true")
        if name == "sync":
            p.add_argument("--runtime", help="path to pinned fanqie-publisher runtime")
            p.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    novel_dir = args.novel_dir.resolve()
    try:
        if args.command == "validate":
            return cmd_validate(novel_dir)
        if args.command == "plan":
            return cmd_plan(novel_dir, args.json)
        if args.command == "sync":
            return cmd_sync(novel_dir, args.runtime, args.dry_run)
    except SyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())