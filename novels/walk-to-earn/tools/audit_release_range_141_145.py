#!/usr/bin/env python3
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "chapters"
TARGET = range(141, 146)
CONTEXT = range(131, 146)

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
TEXT_SYSTEM_RE = re.compile(
    r"有效步数([一二三四五六七八九十百千万零点]+)，收益([一二三四五六七八九十百千万零元角分]+)，累计有效里程([一二三四五六七八九十百千万零点]+)公里"
)

EXPECTED = {
    141: (9476, 1137.12, 1791.2, 0.12),
    142: (7362, 883.44, 1797.1, 0.12),
    143: (9881, 1185.72, 1805.0, 0.12),
    144: (8792, 1055.04, 1812.0, 0.12),
    145: (8334, 1000.08, 1818.7, 0.12),
}

CHINESE_NUM = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
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


def chinese_int(text: str) -> int:
    total = 0
    section = 0
    number = 0
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    for ch in text:
        if ch in CHINESE_NUM:
            number = CHINESE_NUM[ch]
        elif ch in units:
            unit = units[ch]
            if unit == 10000:
                section = (section + number) * 10000
                total += section
                section = 0
                number = 0
            else:
                if number == 0:
                    number = 1
                section += number * unit
                number = 0
    return total + section + number


def chinese_decimal(text: str) -> float:
    if "点" not in text:
        return float(chinese_int(text))
    left, right = text.split("点", 1)
    frac = "".join(str(CHINESE_NUM[c]) for c in right if c in CHINESE_NUM)
    return float(f"{chinese_int(left)}.{frac}")


def chinese_money(text: str) -> float:
    yuan = jiao = fen = 0
    if "元" in text:
        left, text = text.split("元", 1)
        yuan = chinese_int(left)
    if "角" in text:
        left, text = text.split("角", 1)
        jiao = chinese_int(left)
    if "分" in text:
        left = text.split("分", 1)[0]
        fen = chinese_int(left)
    return round(yuan + jiao / 10 + fen / 100, 2)


def settlement(path: Path) -> tuple[int, float, float, float] | None:
    raw = path.read_text(encoding="utf-8")
    matches = SYSTEM_RE.findall(raw)
    if len(matches) == 1:
        steps_s, earned_s, km_s, rate_s = matches[0]
        return int(steps_s), float(earned_s), float(km_s), float(rate_s)
    text_matches = TEXT_SYSTEM_RE.findall(raw)
    if len(text_matches) == 1:
        steps_s, earned_s, km_s = text_matches[0]
        return chinese_int(steps_s), chinese_money(earned_s), chinese_decimal(km_s), 0.12
    return None


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

    cumulative = 1783.6
    for n in TARGET:
        path = ROOT / f"chapter-{n:03d}.md"
        actual = settlement(path)
        expected = EXPECTED[n]
        if actual is None:
            failures.append(f"ch{n}: expected exactly one recognizable settlement, got none or ambiguous")
            continue
        if actual != expected:
            failures.append(f"ch{n}: settlement {actual!r} != expected {expected!r}")
        if round(actual[0] * actual[3], 2) != round(actual[1], 2):
            failures.append(f"ch{n}: {actual[0]} * {actual[3]} != {actual[1]}")
        cumulative = round(cumulative + actual[0] * 0.0008, 1)
        if cumulative != actual[2]:
            failures.append(f"ch{n}: cumulative km {actual[2]} != arithmetic {cumulative}")
        if not (1500 <= actual[2] < 5000):
            failures.append(f"ch{n}: cumulative km outside 0.12-tier range: {actual[2]}")

    if failures:
        print("WALK 141-145 EXACT RELEASE AUDIT: FAIL")
        for item in failures:
            print(f"- {item}")
        return 2

    print("WALK 141-145 EXACT RELEASE AUDIT: PASS")
    print("- no known batch/template markers")
    print("- no suspicious whole-chapter or paragraph duplication vs chapters 131-145")
    print("- no forbidden secondary mechanics")
    print("- all five settlements and cumulative 0.12-tier arithmetic are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
