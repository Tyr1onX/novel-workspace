#!/usr/bin/env python3
"""Plan Walk to Earn release batches against the strict daily release floor.

Default policy:
- at least 3 consecutive chapters per normal day;
- the day's body text must be strictly greater than 6000 non-whitespace characters;
- if 3 chapters do not exceed the floor, an optional consecutive fourth chapter may
  be added only when the active publishing policy supports it;
- fewer than 3 remaining chapters are always held, regardless of their combined length;
- if remaining inventory cannot satisfy both the chapter-count and character floors,
  hold that tail instead of scheduling an invalid release day.

The script is read-only and is intended for CI/audit output before Fanqie
queue authorization.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve()
NOVEL_DIR = HERE.parents[1]
CHAPTER_DIR = NOVEL_DIR / "chapters"
HEADING_RE = re.compile(r"^#\s*第.+?章\s*(.*?)\s*$")
FILE_RE = re.compile(r"chapter-(\d+)\.md$")


def parse_chapter(path: Path) -> dict:
    m = FILE_RE.search(path.name)
    if not m:
        raise ValueError(path)
    number = int(m.group(1))
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        raise RuntimeError(f"empty chapter: {path}")
    heading = HEADING_RE.match(lines[first].strip())
    if not heading:
        raise RuntimeError(f"bad heading: {path}")
    title = heading.group(1).strip()
    body = "\n".join(lines[first + 1 :]).strip()
    chars = len(re.sub(r"\s", "", body))
    return {"number": number, "title": title, "chars": chars}


def load_chapters(start: int, end: int | None) -> list[dict]:
    items = []
    for path in sorted(CHAPTER_DIR.glob("chapter-*.md")):
        item = parse_chapter(path)
        if item["number"] < start:
            continue
        if end is not None and item["number"] > end:
            continue
        items.append(item)
    if not items:
        raise RuntimeError("no chapters in requested range")
    nums = [item["number"] for item in items]
    expected = list(range(nums[0], nums[-1] + 1))
    if nums != expected:
        raise RuntimeError(f"non-consecutive inventory: {nums}")
    return items


def exceeds_floor(total: int, minimum: int) -> bool:
    return total > minimum


def plan(items: list[dict], minimum: int, normal: int, maximum: int) -> dict:
    batches = []
    i = 0
    while i < len(items):
        remaining = len(items) - i
        if remaining < normal:
            tail = items[i:]
            batches.append({
                "chapters": [x["number"] for x in tail],
                "chars": sum(x["chars"] for x in tail),
                "status": "hold",
                "reason": f"fewer than required {normal} chapters remain",
            })
            break

        group = items[i : i + normal]
        total = sum(x["chars"] for x in group)
        if exceeds_floor(total, minimum):
            batches.append({
                "chapters": [x["number"] for x in group],
                "chars": total,
                "status": "ready",
                "reason": f"{normal}-chapter group strictly exceeds daily floor",
            })
            i += normal
            continue

        if maximum > normal and remaining >= maximum:
            group = items[i : i + maximum]
            total = sum(x["chars"] for x in group)
            status = "ready" if exceeds_floor(total, minimum) else "hold"
            batches.append({
                "chapters": [x["number"] for x in group],
                "chars": total,
                "status": status,
                "reason": (
                    "extra consecutive chapter added to strictly exceed daily floor"
                    if status == "ready"
                    else f"even {maximum} chapters do not strictly exceed daily floor"
                ),
            })
            if status == "hold":
                break
            i += maximum
            continue

        tail = items[i:]
        batches.append({
            "chapters": [x["number"] for x in tail],
            "chars": sum(x["chars"] for x in tail),
            "status": "hold",
            "reason": "normal group does not strictly exceed daily floor and no supported larger group is available",
        })
        break

    scheduled_count = sum(
        len(batch["chapters"])
        for batch in batches
        if batch["status"] == "ready"
    )
    return {
        "minimum_chars_exclusive": minimum,
        "comparison": ">",
        "normal_chapters": normal,
        "max_chapters": maximum,
        "inventory": items,
        "batches": batches,
        "all_inventory_schedulable": (
            bool(batches)
            and scheduled_count == len(items)
            and all(batch["status"] == "ready" for batch in batches)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=44)
    parser.add_argument("--end", type=int)
    parser.add_argument("--minimum", type=int, default=6000)
    parser.add_argument("--normal", type=int, default=3)
    parser.add_argument("--maximum", type=int, default=4)
    parser.add_argument("--require-all", action="store_true", help="fail unless all inventory can be scheduled without violating either hard floor")
    args = parser.parse_args()

    if args.minimum < 0:
        raise SystemExit("minimum must be non-negative")
    if not (1 <= args.normal <= args.maximum):
        raise SystemExit("normal/max chapter counts are invalid")
    items = load_chapters(args.start, args.end)
    result = plan(items, args.minimum, args.normal, args.maximum)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.require_all and not result["all_inventory_schedulable"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
