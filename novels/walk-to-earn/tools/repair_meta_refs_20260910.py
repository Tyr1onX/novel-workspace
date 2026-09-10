#!/usr/bin/env python3
"""Remove chapter-number/title references accidentally introduced into body prose.

Scope:
- chapters 113-185 only
- markdown prose body only; headings and fenced code skipped
- no Fanqie upload/sync/publish/runtime code is called
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHAPTER_DIR = ROOT / "novels" / "walk-to-earn" / "chapters"
AUDIT_DIR = ROOT / "novels" / "walk-to-earn" / "audits"
AUDIT_PATH = AUDIT_DIR / "meta-ref-repair-20260910.md"

TITLE_REF_RE = re.compile(r"《第[一二三四五六七八九十百千万零〇两0-9]+章[^》]{0,80}》")
CHAPTER_REF_RE = re.compile(r"第[一二三四五六七八九十百千万零〇两0-9]+章")


def body_chars(text: str) -> int:
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return len(re.sub(r"\s+", "", body))


def repair_line(line: str) -> tuple[str, list[str]]:
    original = line
    hits: list[str] = []
    updated, count = TITLE_REF_RE.subn("这一天", line)
    if count:
        hits.append(f"title refs removed x{count}")
    updated, count = CHAPTER_REF_RE.subn("当天", updated)
    if count:
        hits.append(f"bare chapter refs softened x{count}")
    if updated == original:
        hits.clear()
    return updated, hits


def repair_text(text: str) -> tuple[str, list[str]]:
    out: list[str] = []
    audit: list[str] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or not stripped or stripped.startswith("#"):
            out.append(line)
            continue
        repaired, hits = repair_line(line)
        out.append(repaired)
        if hits:
            audit.append(f"line {line_no}: " + "; ".join(hits))
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + trailing, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=113)
    parser.add_argument("--end", type=int, default=185)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = [
        "# Walk to Earn meta-reference repair audit",
        "",
        "Date: 2026-09-10",
        "Scope: chapters 113-185 only.",
        "Freeze: no Fanqie upload, sync, or publish action is called by this script.",
        "",
    ]
    changed = 0
    total_hits = 0
    for no in range(args.start, args.end + 1):
        path = CHAPTER_DIR / f"chapter-{no:03d}.md"
        text = path.read_text(encoding="utf-8")
        repaired, audit = repair_text(text)
        if repaired != text:
            changed += 1
            total_hits += len(audit)
            report.append(f"## chapter-{no:03d}.md")
            report.append(f"body_chars: {body_chars(text)} -> {body_chars(repaired)}")
            report.extend(f"- {item}" for item in audit)
            report.append("")
            if args.write:
                path.write_text(repaired, encoding="utf-8", newline="\n")
    report.append(f"Changed chapters: {changed}")
    report.append(f"Changed lines: {total_hits}")
    report.append("")
    if args.write:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_PATH.write_text("\n".join(report), encoding="utf-8", newline="\n")
    else:
        print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
