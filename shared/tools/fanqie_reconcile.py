#!/usr/bin/env python3
"""Read-only reconciliation between local novel chapters and Fanqie metadata.

The command opens the saved Playwright session, reads the real cross-volume
chapter list from the pinned fanqie-publisher runtime, compares it with the
repository chapters, and prints a machine-readable report. It never creates,
edits, publishes, deletes, or reschedules a chapter.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import fanqie_probe
import fanqie_sync


class ReconcileError(RuntimeError):
    pass


def _load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    if not script.is_file():
        raise ReconcileError(f"Fanqie runtime script not found: {script}")
    spec = importlib.util.spec_from_file_location("fanqie_runtime_reconcile", script)
    if spec is None or spec.loader is None:
        raise ReconcileError(f"Cannot load Fanqie runtime: {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _platform_title_tail(title: str) -> str:
    title = (title or "").strip()
    title = re.sub(r"^第\s*\d+\s*[章回节话]\s*", "", title).strip()
    title = re.sub(r"^\d+(?=$|[\s:：_\-.、章回节话])\s*", "", title).strip()
    return title


def _epoch_to_local(value, timezone: str) -> str | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return str(value)
    if ts > 10_000_000_000:
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts, ZoneInfo(timezone)).isoformat(timespec="minutes")
    except (OverflowError, OSError, ValueError):
        return str(value)


def _status_name(value) -> str:
    if value == 1:
        return "published"
    if value == 10:
        return "scheduled"
    return f"status_{value}"


async def _read_remote(runtime, book_id: str, headless: bool):
    runtime.load_config()
    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=headless)
        page = await context.new_page()
        try:
            items, _signed_url, volumes = await runtime.fetch_chapter_items(page, book_id)
            # Refresh the local session snapshot after a successful authenticated read.
            await runtime.save_auth(context)
            return items, volumes
        finally:
            await runtime.close_browser_safely(browser)


def _build_report(novel_dir: Path, runtime, items: list[dict], volumes: list[dict], timezone: str):
    config, policy, _queue, local = fanqie_sync.load_model(novel_dir)

    remote_rows = []
    remote_by_num: dict[int, list[dict]] = defaultdict(list)
    status_counts = Counter()
    for item in sorted(items, key=lambda x: x.get("pos", x.get("index", 0))):
        num = runtime.chapter_title_num(item.get("title"))
        status = _status_name(item.get("display_status"))
        status_counts[status] += 1
        row = {
            "position": item.get("pos", item.get("index")),
            "chapter_number": num,
            "title": item.get("title") or "",
            "title_tail": _platform_title_tail(item.get("title") or ""),
            "status": status,
            "display_status": item.get("display_status"),
            "scheduled_at": _epoch_to_local(item.get("timer_time"), timezone),
            "published_or_created_at": _epoch_to_local(item.get("create_time"), timezone),
            "item_id": str(item.get("item_id") or ""),
            "volume_id": str(item.get("volume_id") or ""),
            "volume_name": item.get("volume_name") or "",
        }
        remote_rows.append(row)
        if num is not None:
            remote_by_num[int(num)].append(row)

    local_nums = set(local)
    remote_nums = set(remote_by_num)
    duplicate_nums = {
        str(n): [r["item_id"] for r in rows]
        for n, rows in remote_by_num.items()
        if len(rows) > 1
    }

    title_mismatches = []
    positional_mismatches = []
    for n in sorted(local_nums & remote_nums):
        # Duplicate numbers are reported separately; use the first position only for diagnostics.
        r = remote_by_num[n][0]
        local_title = local[n].title.strip()
        if r["title_tail"].strip() != local_title:
            title_mismatches.append({
                "chapter": n,
                "local_title": local_title,
                "remote_title": r["title"],
            })
    for r in remote_rows:
        n = r["chapter_number"]
        pos = r["position"]
        if n is not None and isinstance(pos, int) and n != pos:
            positional_mismatches.append({
                "position": pos,
                "chapter": n,
                "title": r["title"],
                "status": r["status"],
            })

    scheduled = [
        {
            "chapter": r["chapter_number"],
            "position": r["position"],
            "title": r["title"],
            "scheduled_at": r["scheduled_at"],
            "item_id": r["item_id"],
        }
        for r in remote_rows
        if r["status"] == "scheduled"
    ]

    numbered_remote = [r for r in remote_rows if r["chapter_number"] is not None]
    report = {
        "version": 1,
        "book_id": config["book_id"],
        "timezone": timezone,
        "sync_enabled": bool(config.get("sync_enabled", False)),
        "policy_status": policy.get("policy_status"),
        "local": {
            "chapter_count": len(local),
            "min_chapter": min(local_nums) if local_nums else None,
            "max_chapter": max(local_nums) if local_nums else None,
        },
        "remote": {
            "item_count": len(remote_rows),
            "numbered_item_count": len(numbered_remote),
            "min_chapter": min(remote_nums) if remote_nums else None,
            "max_chapter": max(remote_nums) if remote_nums else None,
            "status_counts": dict(sorted(status_counts.items())),
            "volume_count": max(1, len(volumes or [])),
        },
        "differences": {
            "local_only_chapters": sorted(local_nums - remote_nums),
            "remote_only_chapters": sorted(remote_nums - local_nums),
            "duplicate_remote_chapter_numbers": duplicate_nums,
            "title_mismatches": title_mismatches,
            "position_mismatches": positional_mismatches,
        },
        "scheduled": scheduled,
        "remote_items": remote_rows,
        "content_comparison": {
            "performed": False,
            "reason": "chapter_list exposes metadata, not full chapter body; this pass establishes the safe metadata/schedule baseline",
        },
    }
    return report


def _print_summary(report: dict):
    local = report["local"]
    remote = report["remote"]
    diff = report["differences"]
    print("=== Fanqie reconciliation (READ ONLY) ===")
    print(f"book_id: {report['book_id']}")
    print(f"local chapters: {local['chapter_count']} ({local['min_chapter']}-{local['max_chapter']})")
    print(
        "remote chapters: "
        f"{remote['item_count']} items, numbered {remote['numbered_item_count']} "
        f"({remote['min_chapter']}-{remote['max_chapter']})"
    )
    print(f"remote status counts: {json.dumps(remote['status_counts'], ensure_ascii=False)}")
    print(f"local-only chapters: {fanqie_sync.compact_spec(diff['local_only_chapters']) or '-'}")
    print(f"remote-only chapters: {fanqie_sync.compact_spec(diff['remote_only_chapters']) or '-'}")
    print(f"duplicate remote numbers: {len(diff['duplicate_remote_chapter_numbers'])}")
    print(f"title mismatches: {len(diff['title_mismatches'])}")
    print(f"position mismatches: {len(diff['position_mismatches'])}")
    print(f"scheduled chapters: {len(report['scheduled'])}")
    for row in report["scheduled"]:
        print(
            f"  - 第{row['chapter']}章 | {row['scheduled_at'] or 'time unavailable'} | "
            f"{row['title']}"
        )
    print("NOTE: this pass compares existence/title/order/status/schedule metadata; full body text is not read.")


async def run(novel_dir: Path, runtime_arg: str | None, output: Path | None) -> int:
    config, policy, _queue, _local = fanqie_sync.load_model(novel_dir)
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = _load_runtime(runtime_dir)
    headless = bool((config.get("browser") or {}).get("headless", True))
    timezone = str(policy.get("timezone") or "Asia/Shanghai")

    items, volumes = await _read_remote(runtime, str(config["book_id"]), headless)
    report = _build_report(novel_dir, runtime, items, volumes, timezone)
    _print_summary(report)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"report: {output}")
    print("RECONCILE_JSON_BEGIN")
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    print("RECONCILE_JSON_END")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Fanqie/local reconciliation")
    parser.add_argument("novel_dir", type=Path)
    parser.add_argument("--runtime")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args.novel_dir.resolve(), args.runtime, args.output))
    except (fanqie_probe.ProbeError, fanqie_sync.SyncError, ReconcileError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
