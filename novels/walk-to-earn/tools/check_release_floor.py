#!/usr/bin/env python3
"""Plan Walk to Earn release batches against the 6000-character daily floor.

Default policy:
- 3 consecutive chapters per normal day;
- if those 3 total < 6000 non-whitespace正文 characters, append the next
  consecutive chapter as a fourth chapter;
- if remaining inventory cannot reach 6000 within 4 chapters, hold that tail
  instead of scheduling a sub-floor release day.

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


def plan(items: list[dict], minimum: int, normal: int, maximum: int) -> dict:
    batches = []
    i = 0
    while i < len(items):
        remaining = len(items) - i
        if remaining < normal:
            tail = items[i:]
            total = sum(x["chars"] for x in tail)
            batches.append({
                "chapters": [x["number"] for x in tail],
                "chars": total,
                "status": "ready" if total >= minimum else "hold",
                "reason": None if total >= minimum else "remaining inventory below daily floor",
            })
            break

        group = items[i : i + normal]
        total = sum(x["chars"] for x in group)
        if total >= minimum:
            batches.append({
                "chapters": [x["number"] for x in group],
                "chars": total,
                "status": "ready",
                "reason": "normal three-chapter group meets floor",
            })
            i += normal
            continue

        if remaining >= maximum:
            group = items[i : i + maximum]
            total = sum(x["chars"] for x in group)
            status = "ready" if total >= minimum else "hold"
            batches.append({
                "chapters": [x["number"] for x in group],
                "chars": total,
                "status": status,
                "reason": (
                    "fourth consecutive chapter added to meet floor"
                    if status == "ready"
                    else "even four chapters remain below daily floor"
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
            "reason": "not enough consecutive inventory to add a fourth chapter",
        })
        break

    return {
        "minimum_chars": minimum,
        "normal_chapters": normal,
        "max_chapters": maximum,
        "inventory": items,
        "batches": batches,
        "all_inventory_schedulable": bool(batches) and batches[-1]["status"] == "ready",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=44)
    parser.add_argument("--end", type=int)
    parser.add_argument("--minimum", type=int, default=6000)
    parser.add_argument("--normal", type=int, default=3)
    parser.add_argument("--maximum", type=int, default=4)
    parser.add_argument("--require-all", action="store_true", help="fail if any tail must be held")
    args = parser.parse_args()

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
