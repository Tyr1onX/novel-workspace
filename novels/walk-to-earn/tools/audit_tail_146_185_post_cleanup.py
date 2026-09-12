#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

CHAPTERS = Path(__file__).resolve().parents[1] / "chapters"
START = 146
END = 185
START_CUMULATIVE_KM = 1818.7
RATE = 0.12
KM_PER_STEP = 0.0008

DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
SMALL_UNITS = {"十": 10, "百": 100, "千": 1000}

BRACKET_RE = re.compile(
    r"【今日有效步数：(\d+)】\s*\n"
    r"【今日收益：([0-9]+(?:\.[0-9]+)?)元】\s*\n"
    r"【累计有效里程：([0-9]+(?:\.[0-9]+)?)km】"
    r"(?:\s*\n【当前基础收益：([0-9]+(?:\.[0-9]+)?)元/有效步】)?"
)
TEXT_RE = re.compile(
    r"(?:系统(?:在[^。；\n]{0,20})?(?:结算|弹出|第二次结算|下午结算|晚上结算)[^：:。；\n]{0,20}[：:]?)?"
    r"有效步数([一二两三四五六七八九十百千万零〇点]+)[，,]\s*"
    r"收益([一二两三四五六七八九十百千万零〇元角分点]+)[，,]\s*"
    r"累计有效里程([一二两三四五六七八九十百千万零〇点]+)公里"
)


def chinese_under_10000(text: str) -> int:
    total = 0
    number = 0
    for ch in text:
        if ch in DIGITS:
            number = DIGITS[ch]
        elif ch in SMALL_UNITS:
            unit = SMALL_UNITS[ch]
            total += (number or 1) * unit
            number = 0
    return total + number


def chinese_int(text: str) -> int:
    text = text.replace("〇", "零")
    if "万" in text:
        left, right = text.split("万", 1)
        return chinese_under_10000(left) * 10000 + chinese_under_10000(right)
    return chinese_under_10000(text)


def chinese_decimal(text: str) -> float:
    if "点" not in text:
        return float(chinese_int(text))
    left, right = text.split("点", 1)
    frac = "".join(str(DIGITS[ch]) for ch in right if ch in DIGITS)
    return float(f"{chinese_int(left)}.{frac or '0'}")


def chinese_money(text: str) -> float:
    if "点" in text and not any(u in text for u in "角分"):
        cleaned = text.replace("元", "")
        return chinese_decimal(cleaned)
    yuan = 0
    jiao = 0
    fen = 0
    rest = text
    if "元" in rest:
        left, rest = rest.split("元", 1)
        yuan = chinese_int(left) if left else 0
    if "角" in rest:
        left, rest = rest.split("角", 1)
        jiao = chinese_int(left) if left else 0
    if "分" in rest:
        left = rest.split("分", 1)[0]
        fen = chinese_int(left) if left else 0
    return round(yuan + jiao / 10 + fen / 100, 2)


def extract(raw: str) -> list[tuple[int, float, float, float | None, str]]:
    out: list[tuple[int, float, float, float | None, str]] = []
    for m in BRACKET_RE.finditer(raw):
        out.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)) if m.group(4) else None, "bracket"))
    for m in TEXT_RE.finditer(raw):
        out.append((chinese_int(m.group(1)), chinese_money(m.group(2)), chinese_decimal(m.group(3)), RATE, "text"))
    return out


def main() -> int:
    failures: list[str] = []
    expected_prev = START_CUMULATIVE_KM
    print(f"WALK TAIL NUMERIC AUDIT {START}-{END}; starting anchor ch145={START_CUMULATIVE_KM:.1f}km")
    print("chapter\tsettlements\tsteps\tearned\tobserved_km\texpected_km\tdelta\tstatus")
    for n in range(START, END + 1):
        path = CHAPTERS / f"chapter-{n:03d}.md"
        if not path.exists():
            failures.append(f"ch{n}: missing file")
            print(f"{n}\t0\t-\t-\t-\t-\t-\tMISSING")
            continue
        raw = path.read_text(encoding="utf-8")
        rows = extract(raw)
        if not rows:
            failures.append(f"ch{n}: no recognizable settlement")
            print(f"{n}\t0\t-\t-\t-\t-\t-\tNO_SETTLEMENT")
            continue
        if len(rows) != 1:
            failures.append(f"ch{n}: expected exactly one daily settlement, found {len(rows)}")
        steps, earned, observed_km, rate, style = rows[-1]
        expected_earned = round(steps * RATE, 2)
        expected_km = round(expected_prev + steps * KM_PER_STEP, 1)
        delta = round(observed_km - expected_km, 1)
        status: list[str] = []
        if abs(earned - expected_earned) > 0.001:
            failures.append(f"ch{n}: reward {earned:.2f} != {steps}*{RATE:.2f}={expected_earned:.2f}")
            status.append("REWARD")
        if rate is not None and abs(rate - RATE) > 1e-9:
            failures.append(f"ch{n}: rate {rate} != {RATE}")
            status.append("RATE")
        if observed_km != expected_km:
            failures.append(f"ch{n}: cumulative {observed_km:.1f} != expected {expected_km:.1f} from previous {expected_prev:.1f} + {steps} steps")
            status.append("KM")
        if not (1500 <= observed_km < 5000):
            failures.append(f"ch{n}: observed cumulative {observed_km:.1f} outside 0.12 tier")
            status.append("TIER")
        if len(rows) != 1:
            status.append(f"MULTI({len(rows)})")
        print(f"{n}\t{len(rows)}\t{steps}\t{earned:.2f}\t{observed_km:.1f}\t{expected_km:.1f}\t{delta:+.1f}\t{','.join(status) or 'PASS'} [{style}]")
        # Continuity expectation is derived from actual daily effective steps, not the erroneous observed value.
        expected_prev = expected_km

    print(f"Expected cumulative after ch{END}: {expected_prev:.1f}km")
    if failures:
        print(f"WALK TAIL NUMERIC AUDIT: FAIL ({len(failures)} findings)")
        for item in failures:
            print(f"- {item}")
        return 2
    print("WALK TAIL NUMERIC AUDIT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
