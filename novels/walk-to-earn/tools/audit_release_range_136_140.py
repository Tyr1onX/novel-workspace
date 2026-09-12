#!/usr/bin/env python3
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "chapters"
TARGET = range(136, 141)
CONTEXT = range(131, 141)

FORBIDDEN_TEMPLATE = (
    "这条记录只落在",
    "旁边写着“章节标题”",
    "这一天这天剩下的零碎收回来",
)
FORBIDDEN_MECHANICS = (
    "第二系统",
    "倍率任务",
    "签到奖励",
    "系统宝箱",
    "技能树",
    "身体强化",
    "体质强化",
)
MARKER_RE = re.compile(r"第[0-9一二三四五六七八九十百零]+章第[0-9一二三四五六七八九十百零]+段")
SYSTEM_RE = re.compile(
    r"【今日有效步数：(\d+)】\s*\n"
    r"【今日收益：([0-9]+(?:\.[0-9]+)?)元】\s*\n"
    r"【累计有效里程：([0-9]+(?:\.[0-9]+)?)km】\s*\n"
    r"【当前基础收益：([0-9]+(?:\.[0-9]+)?)元/有效步】"
)

EXPECTED = {
    136: (11997, 1439.64, 1764.3, 0.12),
    139: (15680, 1881.60, 1776.8, 0.12),
    140: (8460, 1015.20, 1783.6, 0.12),
}


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    return "\n".join(lines[1:]).strip()


def paras(text: str) -> list[str]:
    out = []
    for item in re.split(r"\n\s*\n", text):
        n = norm(item)
        if len(n) >= 45 and not n.startswith("【"):
            out.append(n)
    return out


def main() -> int:
    failures: list[str] = []
    texts: dict[int, str] = {}
    paragraphs: dict[int, list[str]] = {}

    for n in CONTEXT:
        path = ROOT / f"chapter-{n:03d}.md"
        if not path.exists():
            failures.append(f"missing chapter-{n:03d}.md")
            continue
        raw = path.read_text(encoding="utf-8")
        b = body(path)
        texts[n] = norm(b)
        paragraphs[n] = paras(b)
        if n in TARGET:
            for token in FORBIDDEN_TEMPLATE:
                if token in raw:
                    failures.append(f"ch{n}: forbidden template token {token!r}")
            if MARKER_RE.search(raw):
                failures.append(f"ch{n}: chapter/paragraph template marker remains")
            for token in FORBIDDEN_MECHANICS:
                if token in raw:
                    failures.append(f"ch{n}: forbidden mechanic token {token!r}")

    for a in TARGET:
        if a not in texts:
            continue
        for b in CONTEXT:
            if b >= a or b not in texts:
                continue
            chapter_ratio = difflib.SequenceMatcher(None, texts[a], texts[b], autojunk=False).ratio()
            if chapter_ratio >= 0.48:
                failures.append(f"ch{a} vs ch{b}: suspicious whole-chapter similarity {chapter_ratio:.3f}")
            hit = False
            for pa in paragraphs[a]:
                for pb in paragraphs[b]:
                    if pa == pb:
                        failures.append(f"ch{a} vs ch{b}: exact repeated paragraph ({len(pa)} chars)")
                        hit = True
                        break
                    ratio = difflib.SequenceMatcher(None, pa, pb, autojunk=False).ratio()
                    if ratio >= 0.90 and min(len(pa), len(pb)) >= 70:
                        failures.append(f"ch{a} vs ch{b}: near-duplicate paragraph similarity {ratio:.3f}")
                        hit = True
                        break
                if hit:
                    break

    for n, expected in EXPECTED.items():
        path = ROOT / f"chapter-{n:03d}.md"
        raw = path.read_text(encoding="utf-8")
        matches = SYSTEM_RE.findall(raw)
        if len(matches) != 1:
            failures.append(f"ch{n}: expected exactly one complete system settlement block, got {len(matches)}")
            continue
        steps_s, earned_s, km_s, rate_s = matches[0]
        actual = (int(steps_s), float(earned_s), float(km_s), float(rate_s))
        if actual != expected:
            failures.append(f"ch{n}: settlement {actual!r} != expected {expected!r}")
        if round(actual[0] * actual[3], 2) != round(actual[1], 2):
            failures.append(f"ch{n}: {actual[0]} * {actual[3]} != {actual[1]}")
        if not (1500 <= actual[2] < 5000):
            failures.append(f"ch{n}: cumulative km outside 0.12-tier range: {actual[2]}")

    for n in (137, 138):
        raw = (ROOT / f"chapter-{n:03d}.md").read_text(encoding="utf-8")
        if SYSTEM_RE.search(raw):
            failures.append(f"ch{n}: unexpected full settlement block; Saturday settlement belongs at ch139")

    # Cumulative arithmetic from the published chapter-135 anchor.
    km136 = round(1754.7 + 11997 * 0.0008, 1)
    km139 = round(km136 + 15680 * 0.0008, 1)
    km140 = round(km139 + 8460 * 0.0008, 1)
    if (km136, km139, km140) != (1764.3, 1776.8, 1783.6):
        failures.append(f"cumulative arithmetic mismatch: {(km136, km139, km140)}")

    if failures:
        print("WALK 136-140 EXACT RELEASE AUDIT: FAIL")
        for item in failures:
            print(f"- {item}")
        return 2

    print("WALK 136-140 EXACT RELEASE AUDIT: PASS")
    print("- no known batch/template markers")
    print("- no suspicious whole-chapter or paragraph duplication vs chapters 131-140")
    print("- no forbidden secondary mechanics")
    print("- system arithmetic and 0.12-tier cumulative anchors are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
