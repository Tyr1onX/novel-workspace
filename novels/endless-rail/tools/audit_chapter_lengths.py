#!/usr/bin/env python3
"""Audit Endless Rail chapter body length.

Policy:
- body only (Markdown heading excluded)
- whitespace removed
- hard minimum: 2000 characters
- no upper length cap
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
    match = FILE_RE.search(path.name)
    if not match:
        raise ValueError(path)
    number = int(match.group(1))
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
    return {"number": number, "heading": heading.lstrip("#").strip(), "chars": chars, "path": str(path)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int)
    ap.add_argument("--hard-minimum", type=int, default=2000)
    ap.add_argument("--fail", action="store_true")
    args = ap.parse_args()

    items = []
    for path in sorted(CHAPTER_DIR.glob("volume-*/*.md")):
        item = parse(path)
        if item["number"] < args.start:
            continue
        if args.end is not None and item["number"] > args.end:
            continue
        item["status"] = "hard-short" if item["chars"] < args.hard_minimum else "ok"
        items.append(item)

    hard = [x for x in items if x["status"] == "hard-short"]
    result = {
        "hard_minimum": args.hard_minimum,
        "hard_maximum": None,
        "count": len(items),
        "hard_count": len(hard),
        "hard_chapters": [x["number"] for x in hard],
        "chapters": items,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.fail and hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
