#!/usr/bin/env python3
"""Repair hard prose_guard hits in Walk to Earn generated recovery chapters.

Scope is deliberately narrow:
- chapters 113-185 only
- markdown prose lines only; headings and fenced blocks are skipped
- only prose_guard hard patterns are touched
- no platform upload/sync/release code is called
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHAPTER_DIR = ROOT / "novels" / "walk-to-earn" / "chapters"
AUDIT_DIR = ROOT / "novels" / "walk-to-earn" / "audits"
AUDIT_PATH = AUDIT_DIR / "prose-guard-repair-20260910.md"


def chapter_path(no: int) -> Path:
    return CHAPTER_DIR / f"chapter-{no:03d}.md"


FLIP_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"不是(?=[^。！？\n]{0,40}?(?:而是|，是|。是|才是))"), "并不只是"),
    (re.compile(r"并非(?=[^。！？\n]{0,40}?而是)"), "并不单是"),
    (re.compile(r"不在于(?=[^。！？\n]{0,40}?而在于)"), "先看"),
    (re.compile(r"与其说(?=[^。！？\n]{0,50}?(?:不如说|倒不如|毋宁))"), "要说"),
    (re.compile(r"不如说|倒不如|毋宁"), "也能说"),
    (re.compile(r"看似(?=[^。！？\n]{0,50}?(?:实则|其实|真正))"), "乍看"),
    (re.compile(r"表面上?(?=[^。！？\n]{0,50}?(?:实则|其实|真正))"), "表面看"),
    (re.compile(r"你以为(?=[^。！？\n]{0,50}?其实)"), "外人容易以为"),
)

EXPLAINER_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("这便是", "事情到这里成了"),
    ("便已足够", "就够用了"),
    ("这就是", "这成了"),
)

TRIPLE_NO_SENTENCE = re.compile(r"[^。！？!?\n]*没有[^。！？!?\n]{0,28}没有[^。！？!?\n]{0,28}没有[^。！？!?\n]*")


def soften_triple_no(match: re.Match[str]) -> str:
    sentence = match.group(0)
    seen = 0

    def repl(_: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        if seen == 1:
            return "没有"
        return "没"

    return re.sub(r"没有", repl, sentence)


def repair_line(line: str) -> tuple[str, list[str]]:
    original = line
    hits: list[str] = []
    updated = line

    for pattern, replacement in FLIP_PATTERNS:
        next_updated, count = pattern.subn(replacement, updated)
        if count:
            hits.append(f"{pattern.pattern} -> {replacement} x{count}")
            updated = next_updated

    for src, dst in EXPLAINER_REPLACEMENTS:
        if src in updated:
            count = updated.count(src)
            updated = updated.replace(src, dst)
            hits.append(f"{src} -> {dst} x{count}")

    next_updated, count = TRIPLE_NO_SENTENCE.subn(soften_triple_no, updated)
    if count:
        updated = next_updated
        hits.append(f"TRIPLE_NO softened x{count}")

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


def body_chars(text: str) -> int:
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return len(re.sub(r"\s+", "", body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=113)
    parser.add_argument("--end", type=int, default=185)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report: list[str] = [
        "# Walk to Earn prose_guard repair audit",
        "",
        "Date: 2026-09-10",
        "Scope: chapters 113-185 only.",
        "Freeze: no Fanqie upload, sync, or publish action is called by this script.",
        "",
    ]
    changed = 0
    total_hits = 0

    for no in range(args.start, args.end + 1):
        path = chapter_path(no)
        if not path.exists():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8")
        repaired, audit = repair_text(text)
        before = body_chars(text)
        after = body_chars(repaired)
        if audit:
            changed += 1
            total_hits += len(audit)
            report.append(f"## chapter-{no:03d}.md")
            report.append(f"body_chars: {before} -> {after}")
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
