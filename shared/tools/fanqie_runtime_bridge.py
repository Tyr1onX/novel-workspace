#!/usr/bin/env python3
"""Run the pinned Fanqie publisher with repository-owned scheduling semantics.

Upstream intentionally makes every chapter time unique (e.g. 00:00/00:01/00:02).
The author's established Fanqie habit is different: a release group of chapters is
intentionally scheduled at the exact same 00:00 timestamp. This bridge keeps the
upstream browser/publish implementation intact and replaces only the scheduling
semantics explicitly owned by the repository.

For rescheduling, the bridge skips chapters whose existing platform date/time is
already exactly the requested target. It also plans the remaining writes by target
day dependencies instead of accepting the chapter table's newest-first DOM order.
That matters when a reflow moves old chapters out of a date while moving newer
chapters into it: filling the date first can temporarily exceed Fanqie's daily word
limit even though the final release group itself is valid.
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


def build_safe_reschedule_plan(rows, schedule_map):
    """Return (filtered_map, skipped_titles, target_day_order) for a safe reflow.

    Fanqie's chapter table is newest-first and upstream mutates in that DOM order.
    During a compaction this can fill a target day before its old occupants have been
    moved away, tripping the platform's daily word limit. A target day therefore
    depends on the destination days of any requested chapters that currently occupy
    it. Processing a topological order of those day dependencies drains blockers
    before filling the day.

    The planner is intentionally fail-closed. If a target day is occupied by a chapter
    outside the requested schedule, or the dependency graph contains a cycle, it does
    not fall back to upstream's unsafe order.
    """
    by_title = {}
    for row in rows:
        title = str(row.get("title") or "").strip()
        if title:
            by_title[title] = row

    filtered = {}
    skipped = []
    target_day_by_title = {}
    group_days = []
    for title, target in schedule_map.items():
        clean_title = str(title).strip()
        desired = (str(target[0]), str(target[1]))
        target_day_by_title[clean_title] = desired[0]
        row = by_title.get(clean_title)
        current = _row_datetime(row or {})
        if row is not None and current == desired:
            skipped.append(title)
            continue
        filtered[title] = target
        if desired[0] not in group_days:
            group_days.append(desired[0])

    if not filtered:
        return filtered, skipped, []

    group_set = set(group_days)
    dependencies = {day: set() for day in group_days}

    for row in rows:
        title = str(row.get("title") or "").strip()
        current_day, _current_time = _row_datetime(row)
        if not current_day or current_day not in group_set:
            continue
        if title not in target_day_by_title:
            raise BridgeError(
                f"unsafe reschedule: target day {current_day} is occupied by "
                f"unmanaged chapter {title!r}"
            )
        destination_day = target_day_by_title[title]
        if destination_day == current_day:
            continue
        if destination_day not in group_set:
            raise BridgeError(
                f"unsafe reschedule: blocker {title!r} on {current_day} moves to "
                f"unplanned target day {destination_day}"
            )
        dependencies[current_day].add(destination_day)

    rank = {day: i for i, day in enumerate(group_days)}
    pending = set(group_days)
    ordered = []
    while pending:
        ready = [
            day
            for day in group_days
            if day in pending and not (dependencies[day] & pending)
        ]
        if not ready:
            detail = ", ".join(
                f"{day}<-{','.join(sorted(dependencies[day] & pending))}"
                for day in group_days
                if day in pending
            )
            raise BridgeError(f"unsafe reschedule: target-day dependency cycle: {detail}")
        ready.sort(key=lambda day: rank[day])
        for day in ready:
            ordered.append(day)
            pending.remove(day)

    return filtered, skipped, ordered


async def reset_manage_page_for_inspection(runtime, page, book_id) -> None:
    """Return the shared browser page to a stable chapter-list entry point.

    Upstream performs its own full-table scan before calling the patched rescheduler.
    That scan leaves the SPA on whichever pagination page it finished on. Running the
    extractor again from that inherited middle-page state can return an empty/partial
    set, which defeats the bridge's idempotent filtering. Reload the canonical manage
    URL first and fail closed if the stable table cannot be restored.
    """
    url_tpl = getattr(runtime, "CHAPTER_MANAGE_URL_TPL", None)
    settle = getattr(runtime, "settle_page", None)
    if not url_tpl or settle is None:
        raise BridgeError("pinned Fanqie runtime is missing chapter-manage reset hooks")

    url = str(url_tpl).format(book_id=book_id)
    try:
        await page.goto(url)
        await settle(page)
        wait_for_selector = getattr(page, "wait_for_selector", None)
        if wait_for_selector is not None:
            timeout = int(getattr(runtime, "_browser_timeout", 10000) or 10000)
            await wait_for_selector("tr td", timeout=timeout)
    except BridgeError:
        raise
    except Exception as exc:
        raise BridgeError(
            f"cannot reset chapter manage page before safe inspection: {exc}"
        ) from exc


def patch_reschedule_noops(runtime) -> None:
    original = getattr(runtime, "reschedule_on_manage_page", None)
    extractor = getattr(runtime, "extract_chapters_from_page", None)
    if original is None or extractor is None:
        raise BridgeError("pinned Fanqie runtime is missing reschedule/extractor hooks")

    async def filtered_reschedule(page, book_id, schedule_map, **kwargs):
        volume_texts = kwargs.get("volume_texts")
        if volume_texts and len(volume_texts) > 1:
            raise BridgeError(
                "safe reschedule ordering is not implemented for multi-volume books"
            )

        try:
            await reset_manage_page_for_inspection(runtime, page, book_id)
            rows, _last = await extractor(page, book_id)
            if not rows:
                raise BridgeError(
                    "safe reschedule inspection returned zero chapter rows after page reset"
                )
            filtered, skipped, day_order = build_safe_reschedule_plan(rows, schedule_map)
        except BridgeError:
            raise
        except Exception as exc:
            raise BridgeError(
                f"cannot inspect current platform schedule safely: {exc}"
            ) from exc

        if skipped:
            runtime.logger.info(
                f"排期幂等检查：{len(skipped)} 章已处于目标时间，跳过重复提交"
            )
        if not filtered:
            runtime.logger.info("排期幂等检查：全部待发布章节已符合目标排期，无需修改")
            return 0, 0

        runtime.logger.info(
            "安全排期顺序：" + " -> ".join(day_order)
            + f"（实际需修改 {len(filtered)} 章）"
        )
        success = 0
        for index, day in enumerate(day_order, 1):
            subset = {
                title: target
                for title, target in filtered.items()
                if str(target[0]) == day
            }
            if not subset:
                continue
            runtime.logger.info(
                f"安全排期组 [{index}/{len(day_order)}] {day}: {len(subset)} 章"
            )
            ok, bad = await original(page, book_id, subset, **kwargs)
            success += ok
            if bad != 0 or ok != len(subset):
                raise BridgeError(
                    f"safe reschedule group {day} incomplete: "
                    f"expected={len(subset)}, success={ok}, failed={bad}"
                )
        return success, 0

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
