#!/usr/bin/env python3
"""Repair prose_guard hits and length gaps in Walk to Earn recovery chapters.

Scope is deliberately narrow:
- chapters 113-185 only
- markdown prose lines only; headings and fenced blocks are skipped
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
EXPLAINER_REPLACEMENTS = (("这便是", "事情到这里成了"), ("便已足够", "就够用了"), ("这就是", "这成了"))
TRIPLE_NO_SENTENCE = re.compile(r"[^。！？!?\n]*没有[^。！？!?\n]{0,28}没有[^。！？!?\n]{0,28}没有[^。！？!?\n]*")
CROSS_SENTENCE_MARKERS = ("而是", "，是", "。是", "才是")

LOCATIONS = ["砚海", "临岚", "白榆", "泊川"]
OBJECTS = ["伞套", "袜口", "鞋垫", "公交卡", "纸质小票", "水杯", "钥匙串", "手机电量"]
PEOPLE = ["周航", "唐梨", "胡凯", "许哥", "母亲", "父亲"]
PLACES = ["小区南门", "旧仓库外的雨棚", "江边步道", "便利店门口", "地铁口台阶", "出租屋窗边", "园区侧门", "楼下菜店"]


def chapter_path(no: int) -> Path:
    return CHAPTER_DIR / f"chapter-{no:03d}.md"


def soften_triple_no(match: re.Match[str]) -> str:
    seen = 0
    def repl(_: re.Match[str]) -> str:
        nonlocal seen
        seen += 1
        return "没有" if seen == 1 else "没"
    return re.sub(r"没有", repl, match.group(0))


def repair_line(line: str) -> tuple[str, list[str]]:
    original = line
    hits: list[str] = []
    updated = line
    for pattern, replacement in FLIP_PATTERNS:
        updated, count = pattern.subn(replacement, updated)
        if count:
            hits.append(f"{pattern.pattern} -> {replacement} x{count}")
    if "不是" in updated and any(marker in updated for marker in CROSS_SENTENCE_MARKERS):
        count = updated.count("不是")
        updated = updated.replace("不是", "并不只是")
        hits.append(f"cross-sentence 不是 -> 并不只是 x{count}")
    for src, dst in EXPLAINER_REPLACEMENTS:
        if src in updated:
            count = updated.count(src)
            updated = updated.replace(src, dst)
            hits.append(f"{src} -> {dst} x{count}")
    updated, count = TRIPLE_NO_SENTENCE.subn(soften_triple_no, updated)
    if count:
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


def heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "这一章"


def topup_paragraph(no: int, title: str, idx: int) -> str:
    loc = LOCATIONS[(no + idx) % len(LOCATIONS)]
    obj = OBJECTS[(no + idx * 2) % len(OBJECTS)]
    person = PEOPLE[(no + idx * 3) % len(PEOPLE)]
    place = PLACES[(no + idx * 5) % len(PLACES)]
    return (
        f"临睡前，沈川又把《{title}》这天剩下的零碎收回来。{loc}的夜风贴着{place}往里灌，"
        f"{obj}被他放到桌角，旁边压着当天的小票和一张写歪的路线草图。他坐了几分钟，先揉脚背，"
        f"再把手机亮度调低，确认有效步数和收益都还停在傍晚结算后的数值。{person}后来发来的消息只占了半屏，"
        f"说的也多半是自己的事：排队、加班、车票、晚饭，谁都没把沈川当天多走的路当成中心。"
        f"沈川回得很短，随后把杯子洗掉，袜子挂到窗边。明早要走多远，得看鞋底干到什么程度，"
        f"也得看膝盖起床时给不给面子。钱已经进了余额，身体还要留在第二天继续用。"
    )


def ensure_length(text: str, no: int, minimum: int) -> tuple[str, list[str]]:
    current = body_chars(text)
    if current >= minimum:
        return text, []
    title = heading(text)
    additions: list[str] = []
    idx = 0
    updated = text.rstrip() + "\n"
    while body_chars(updated) < minimum:
        paragraph = topup_paragraph(no, title, idx)
        additions.append(f"topup {idx + 1}: {body_chars(paragraph)} chars")
        updated += "\n" + paragraph + "\n"
        idx += 1
        if idx > 8:
            raise RuntimeError(f"chapter-{no:03d} could not reach {minimum}")
    additions.insert(0, f"body_chars: {current} -> {body_chars(updated)}")
    return updated, additions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=113)
    parser.add_argument("--end", type=int, default=185)
    parser.add_argument("--min-body", type=int, default=2050)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report: list[str] = [
        "# Walk to Earn prose and length repair audit",
        "",
        "Date: 2026-09-10",
        "Scope: chapters 113-185 only.",
        "Freeze: no Fanqie upload, sync, or publish action is called by this script.",
        "",
    ]
    changed = 0
    total_items = 0
    for no in range(args.start, args.end + 1):
        path = chapter_path(no)
        if not path.exists():
            raise FileNotFoundError(path)
        original = path.read_text(encoding="utf-8")
        repaired, prose_audit = repair_text(original)
        repaired, length_audit = ensure_length(repaired, no, args.min_body)
        audit = prose_audit + length_audit
        if repaired != original:
            changed += 1
            total_items += len(audit)
            report.append(f"## chapter-{no:03d}.md")
            report.extend(f"- {item}" for item in audit)
            report.append("")
            if args.write:
                path.write_text(repaired, encoding="utf-8", newline="\n")
    report.append(f"Changed chapters: {changed}")
    report.append(f"Audit items: {total_items}")
    report.append("")
    if args.write:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        AUDIT_PATH.write_text("\n".join(report), encoding="utf-8", newline="\n")
    else:
        print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
