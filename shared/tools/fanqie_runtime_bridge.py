#!/usr/bin/env python3
"""Run the pinned Fanqie publisher with repository-owned scheduling semantics.

Upstream intentionally makes every chapter time unique (e.g. 00:00/00:01/00:02).
The author's established Fanqie habit is different: a release group of three chapters
is intentionally scheduled at the exact same 00:00 timestamp. This bridge keeps the
upstream browser/publish implementation intact and replaces only the scheduling
semantics explicitly owned by the repository.

For rescheduling, the bridge also skips chapters whose existing platform date/time is
already exactly the requested target. This makes retries idempotent and avoids sending
no-op modify-timer requests, which Fanqie can reject with a misleading server-error
message.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path


class BridgeError(RuntimeError):
    pass


def load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    if not script.is_file():
        raise BridgeError(f"Fanqie runtime script not found: {script}")
    spec = importlib.util.spec_from_file_location("fanqie_runtime_bridge_target", script)
    if spec is None or spec.loader is None:
        raise BridgeError(f"Cannot load Fanqie runtime: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, script


def exact_group_schedule(file_count: int, start_date: str, exact_time: str, group_size: int):
    if file_count < 0:
        raise BridgeError("file_count must be non-negative")
    if group_size < 1:
        raise BridgeError("group_size must be positive")
    try:
        base = datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(exact_time, "%H:%M")
    except ValueError as exc:
        raise BridgeError(str(exc)) from exc
    return [
        (
            (base + timedelta(days=i // group_size)).strftime("%Y-%m-%d"),
            exact_time,
        )
        for i in range(file_count)
    ]


def _row_datetime(row):
    date = str(row.get("date") or "").strip()
    time = str(row.get("time") or "").strip()
    if date and time:
        return date, time
    value = str(row.get("scheduled_at") or row.get("scheduledAt") or "").strip()
    if "T" in value:
        left, right = value.split("T", 1)
        return left[:10], right[:5]
    return date, time


def patch_reschedule_noops(runtime) -> None:
    original = getattr(runtime, "reschedule_on_manage_page", None)
    extractor = getattr(runtime, "extract_chapters_from_page", None)
    if original is None or extractor is None:
        return

    async def filtered_reschedule(page, book_id, schedule_map, **kwargs):
        # The current production books are single-volume. For a true multi-volume
        # invocation, preserve upstream behavior unless we can inspect the whole
        # requested set in one table view; correctness is more important than an
        # optimization.
        volume_texts = kwargs.get("volume_texts")
        if volume_texts and len(volume_texts) > 1:
            return await original(page, book_id, schedule_map, **kwargs)

        try:
            rows, _last = await extractor(page, book_id)
            by_title = {
                str(row.get("title") or "").strip(): row
                for row in rows
                if str(row.get("title") or "").strip()
            }
            filtered = {}
            skipped = []
            for title, target in schedule_map.items():
                row = by_title.get(str(title).strip())
                current = _row_datetime(row or {})
                desired = (str(target[0]), str(target[1]))
                if row is not None and current == desired:
                    skipped.append(title)
                    continue
                filtered[title] = target

            if skipped:
                runtime.logger.info(
                    f"排期幂等检查：{len(skipped)} 章已处于目标时间，跳过重复提交"
                )
            if not filtered:
                runtime.logger.info("排期幂等检查：全部待发布章节已符合目标排期，无需修改")
                return 0, 0
            return await original(page, book_id, filtered, **kwargs)
        except Exception as exc:
            # Fail open only for this optimization: if platform DOM extraction changes,
            # fall back to the pinned upstream rescheduler rather than guessing that a
            # chapter is already correct.
            runtime.logger.warning(f"排期幂等检查不可用，回退上游重排逻辑: {exc}")
            return await original(page, book_id, schedule_map, **kwargs)

    runtime.reschedule_on_manage_page = filtered_reschedule


def main() -> int:
    parser = argparse.ArgumentParser(description="Repository scheduling bridge for Fanqie publisher")
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--same-time-group-size", type=int, required=True)
    parser.add_argument("--same-time", required=True)
    parser.add_argument("upstream_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    upstream_args = list(args.upstream_args)
    if upstream_args and upstream_args[0] == "--":
        upstream_args.pop(0)
    if not upstream_args:
        raise BridgeError("missing upstream fanqie-publisher arguments")

    runtime, script = load_runtime(args.runtime.resolve())
    group_size = int(args.same_time_group_size)
    exact_time = str(args.same_time)
    original_compute = runtime.compute_schedule

    def patched_compute(file_count: int, start_date: str, pub_time: str, per_day: int):
        times = runtime.validate_times(pub_time)
        if per_day == group_size and times == [exact_time]:
            schedule = exact_group_schedule(file_count, start_date, exact_time, group_size)
            runtime.logger.info(
                "排期：按仓库策略保留同组相同发布时间 "
                f"({group_size} 章/组，{exact_time})"
            )
            return schedule
        # Fail closed to upstream's conservative unique-time scheduler whenever the
        # invocation does not exactly match the repository policy we were asked to patch.
        return original_compute(file_count, start_date, pub_time, per_day)

    runtime.compute_schedule = patched_compute
    patch_reschedule_noops(runtime)

    old_argv = sys.argv[:]
    try:
        sys.argv = [str(script), *upstream_args]
        result = runtime.main()
        return int(result or 0)
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BridgeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
