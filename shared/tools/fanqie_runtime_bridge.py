#!/usr/bin/env python3
"""Run the pinned Fanqie publisher with repository-owned scheduling semantics.

Upstream intentionally makes every chapter time unique (e.g. 00:00/00:01/00:02).
The author's established Fanqie habit is different: a release group of three chapters
is intentionally scheduled at the exact same 00:00 timestamp.  This bridge keeps the
upstream browser/publish implementation intact and replaces only its pure
`compute_schedule` function for explicitly configured same-time groups.
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
