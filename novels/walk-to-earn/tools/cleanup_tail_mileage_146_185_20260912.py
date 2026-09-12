from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import re

ROOT = Path("novels/walk-to-earn/chapters")
AUDIT = Path("novels/walk-to-earn/audits/tail-mileage-cleanup-146-185-20260912.md")
START, END = 146, 185
cumulative = Decimal("1818.7")

digit_map = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
unit_map = {"十": 10, "百": 100, "千": 1000}


def cn_to_int(s: str) -> int:
    total = 0
    section = 0
    number = 0
    for ch in s:
        if ch in digit_map:
            number = digit_map[ch]
        elif ch in unit_map:
            unit = unit_map[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
        elif ch == "万":
            section += number
            total += section * 10000
            section = 0
            number = 0
    return total + section + number


def int_to_cn(n: int) -> str:
    if n == 0:
        return "零"
    digits = "零一二三四五六七八九"

    def under_10000(x: int) -> str:
        units = [(1000, "千"), (100, "百"), (10, "十"), (1, "")]
        out = []
        zero_pending = False
        for value, label in units:
            d, x = divmod(x, value)
            if d:
                if zero_pending and out:
                    out.append("零")
                if not (value == 10 and d == 1 and not out):
                    out.append(digits[d])
                out.append(label)
                zero_pending = False
            elif out and x:
                zero_pending = True
        return "".join(out)

    if n < 10000:
        return under_10000(n)
    hi, lo = divmod(n, 10000)
    out = int_to_cn(hi) + "万"
    if lo:
        if lo < 1000:
            out += "零"
        out += under_10000(lo)
    return out


def dec_to_cn(x: Decimal) -> str:
    q = x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    whole = int(q)
    frac = int((q - whole) * 10)
    return f"{int_to_cn(whole)}点{int_to_cn(frac)}"


def extract_steps(text: str, chapter: int) -> int:
    patterns = [
        r"【今日有效步数[：:]\s*(\d+)】",
        r"有效步数(?:为|是)?[：:\s]*([0-9]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return int(m.group(1))
    m = re.search(r"有效步数(?:为|是)?[：:\s]*([零〇一二两三四五六七八九十百千万]+)", text)
    if m:
        return cn_to_int(m.group(1))
    raise RuntimeError(f"chapter {chapter}: cannot find effective steps")


filler_markers = (
    "这一天这天剩下的零碎收回来",
    "写歪的路线草图",
    "膝盖起床时给不给面子",
    "钱已经进了余额，身体还要留在第二天继续用",
)

report = [
    "# Walk 146–185 repeated-tail and cumulative-mileage cleanup",
    "",
    "Scope is strictly chapters 146–185. No platform mutation is performed.",
    "",
    "Starting displayed cumulative mileage: chapter 145 = 1818.7 km.",
    "Each effective step contributes 0.0008 km; displayed cumulative mileage is rounded to one decimal using half-up rounding.",
    "",
    "| chapter | steps | removed filler paragraphs | new cumulative km |",
    "|---:|---:|---:|---:|",
]

changed = []
for n in range(START, END + 1):
    path = ROOT / f"chapter-{n}.md"
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    chunks = re.split(r"\n\s*\n", text)
    kept = []
    removed = 0
    for chunk in chunks:
        score = sum(1 for marker in filler_markers if marker in chunk)
        if score >= 2:
            removed += 1
            continue
        kept.append(chunk.strip())
    text2 = "\n\n".join(c for c in kept if c) + "\n"

    steps = extract_steps(text2, n)
    cumulative += Decimal(steps) * Decimal("0.0008")
    shown = cumulative.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    if re.search(r"【累计有效里程[：:]\s*[0-9.]+\s*km】", text2):
        text2 = re.sub(
            r"【累计有效里程[：:]\s*[0-9.]+\s*km】",
            f"【累计有效里程：{shown}km】",
            text2,
            count=1,
        )
    elif re.search(r"累计有效里程(?:为|是)?[：:\s]*[零〇一二两三四五六七八九十百千万点]+公里", text2):
        text2 = re.sub(
            r"累计有效里程(?:为|是)?[：:\s]*[零〇一二两三四五六七八九十百千万点]+公里",
            f"累计有效里程{dec_to_cn(shown)}公里",
            text2,
            count=1,
        )
    elif re.search(r"累计有效里程(?:为|是)?[：:\s]*[0-9.]+公里", text2):
        text2 = re.sub(
            r"累计有效里程(?:为|是)?[：:\s]*[0-9.]+公里",
            f"累计有效里程{shown}公里",
            text2,
            count=1,
        )
    else:
        raise RuntimeError(f"chapter {n}: cannot find cumulative mileage field")

    if text2 != text:
        path.write_text(text2, encoding="utf-8", newline="\n")
        changed.append(n)
    report.append(f"| {n} | {steps} | {removed} | {shown} |")

report += [
    "",
    f"Changed chapters: {', '.join(map(str, changed)) if changed else 'none'}.",
    "",
    "Publishing remains frozen pending post-cleanup automated gates and manual cold read.",
]
AUDIT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
print("changed:", changed)
