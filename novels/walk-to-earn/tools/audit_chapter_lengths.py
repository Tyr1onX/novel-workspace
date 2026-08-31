#!/usr/bin/env python3
"""Audit Walk to Earn chapter body length.

Length policy:
- body only (Markdown heading excluded)
- whitespace removed
- hard minimum: 2000 characters
- practical writing target is higher; this script only enforces/reports the hard floor.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve()
NOVEL_DIR = HERE.parents[1]
CHAPTER_DIR = NOVEL_DIR / "chapters"
FILE_RE = re.compile(r"chapter-(\d+)\.md$")


def parse(path: Path) -> dict:
    m = FILE_RE.search(path.name)
    if not m:
        raise ValueError(path)
    number = int(m.group(1))
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        raise RuntimeError(f"empty chapter: {path}")
    heading = lines[first].strip()
    if not heading.startswith("#"):
        raise RuntimeError(f"missing heading: {path}")
    body = "\n".join(lines[first + 1 :]).strip()
    chars = len(re.sub(r"\s", "", body))
    return {"number": number, "heading": heading.lstrip("#").strip(), "chars": chars}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minimum", type=int, default=2000)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int)
    ap.add_argument("--fail", action="store_true")
    args = ap.parse_args()

    items = []
    for path in sorted(CHAPTER_DIR.glob("chapter-*.md")):
        item = parse(path)
        if item["number"] < args.start:
            continue
        if args.end is not None and item["number"] > args.end:
            continue
        item["status"] = "pass" if item["chars"] >= args.minimum else "short"
        item["deficit"] = max(0, args.minimum - item["chars"])
        items.append(item)

    short = [x for x in items if x["status"] == "short"]
    result = {
        "minimum_chars": args.minimum,
        "count": len(items),
        "pass_count": len(items) - len(short),
        "short_count": len(short),
        "short_chapters": [x["number"] for x in short],
        "chapters": items,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.fail and short else 0


if __name__ == "__main__":
    raise SystemExit(main())
