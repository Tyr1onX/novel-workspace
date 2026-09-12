from pathlib import Path
import re

ROOT = Path("novels/walk-to-earn/chapters")
AUDIT = Path("novels/walk-to-earn/audits/repeated-tail-cleanup-146-185-20260912.md")
START, END = 146, 185

filler_markers = (
    "这一天这天剩下的零碎收回来",
    "写歪的路线草图",
    "膝盖起床时给不给面子",
    "钱已经进了余额，身体还要留在第二天继续用",
)

report = [
    "# Walk 146–185 repeated-tail cleanup",
    "",
    "Scope is strictly chapters 146–185. No cumulative-mileage value is changed, and no platform mutation is performed.",
    "",
    "A paragraph is removed only when it contains at least two known generated-filler markers.",
    "",
    "| chapter | removed filler paragraphs |",
    "|---:|---:|",
]

changed = []
total_removed = 0
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
    if text2 != text:
        path.write_text(text2, encoding="utf-8", newline="\n")
        changed.append(n)
    total_removed += removed
    report.append(f"| {n} | {removed} |")

report += [
    "",
    f"Total removed filler paragraphs: {total_removed}.",
    f"Changed chapters: {', '.join(map(str, changed)) if changed else 'none'}.",
    "",
    "Publishing remains frozen pending post-cleanup length, narrative, dialogue, humanizer, prose, meta, similarity, continuity, and manual cold-read audits.",
]
AUDIT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
print("changed:", changed)
print("removed:", total_removed)
