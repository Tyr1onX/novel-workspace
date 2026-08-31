#!/usr/bin/env python3
"""Heuristic Narrative Pass reviewer for novel-workspace.

This guard is deliberately advisory in V1. It locates patterns that deserve
human review before sentence-level humanization, but narrative texture cannot
be judged safely by regex alone.

Usage:
    python shared/tools/narrative_guard.py chapter-001.md [chapter-002.md ...]

Exit codes:
    0: files were reviewed (REVIEW findings may still be printed)
    2: one or more files could not be read
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


BODY_PATTERNS = (
    r"心(?:脏|跳|口|头)[^。！？\n]{0,10}(?:一紧|一沉|一跳|狂跳|漏了|发紧|发慌)",
    r"呼吸[^。！？\n]{0,10}(?:一滞|停了|急促|发紧|乱了|屏住)",
    r"胸口[^。！？\n]{0,10}(?:一紧|发紧|发闷|堵|沉)",
    r"喉(?:咙|结)[^。！？\n]{0,10}(?:发干|发紧|滚动|动了|堵)",
    r"(?:指尖|手心|掌心)[^。！？\n]{0,10}(?:发凉|冰凉|冒汗|出汗|发麻|攥紧)",
    r"脊背[^。！？\n]{0,10}(?:发凉|一寒|冒汗|绷紧)",
    r"胃里[^。！？\n]{0,10}(?:一沉|发紧|翻腾|抽|不舒服)",
    r"太阳穴[^。！？\n]{0,10}(?:跳|突突|发胀)",
)

DIRECT_EMOTIONS = (
    "烦", "害怕", "怕了", "后悔", "尴尬", "丢脸", "难受", "生气", "火大",
    "委屈", "舍不得", "紧张", "慌", "担心", "失望", "高兴", "开心", "嫉妒",
    "不爽", "恼火", "羞愧", "心虚", "厌烦", "焦躁", "无奈",
)

CLOSURE_PATTERNS = (
    r"这(?:就)?意味着",
    r"这(?:也)?说明",
    r"他这才(?:意识到|明白|懂得)",
    r"她这才(?:意识到|明白|懂得)",
    r"真正(?:的|的问题|重要的|意味着)",
    r"本质上",
    r"归根结底",
    r"说到底",
    r"某种变化(?:正在|已经)",
    r"新的(?:生活|阶段|开始|篇章)(?:才)?刚刚开始",
)

CAUSAL_WORDS = (
    "因此", "所以", "于是", "随后", "接着", "最终", "因而", "从而", "这才", "然后",
)

DIALOGUE_ABSTRACT_WORDS = (
    "人生", "命运", "意义", "本质", "真正", "选择", "成长", "未来", "自由", "价值",
    "证明", "改变", "世界", "遗憾", "失去", "拥有",
)

QUOTE_RE = re.compile(r"[“\"]([^”\"\n]{2,160})[”\"]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])")


@dataclass
class Finding:
    label: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review narrative-level AI-pattern risks without auto-rewriting."
    )
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 chapter markdown/text files")
    return parser.parse_args()


def count_regexes(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(re.findall(pattern, text)) for pattern in patterns)


def nonempty_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", text):
        cleaned = raw.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        paragraphs.append(cleaned)
    return paragraphs


def first_sentence(paragraph: str) -> str:
    line = " ".join(piece.strip() for piece in paragraph.splitlines() if piece.strip())
    if not line:
        return ""
    parts = SENTENCE_SPLIT_RE.split(line, maxsplit=1)
    sentence = parts[0].strip()
    return sentence[:100] + ("…" if len(sentence) > 100 else "")


def review_text(text: str) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    paragraphs = nonempty_paragraphs(text)
    char_count = max(len(re.sub(r"\s+", "", text)), 1)

    body_hits = count_regexes(text, BODY_PATTERNS)
    direct_hits = sum(text.count(word) for word in DIRECT_EMOTIONS)
    body_rate = body_hits * 3000 / char_count
    if body_hits >= 5 and body_rate >= 3.0:
        note = (
            f"身体化情绪信号 {body_hits} 次（约 {body_rate:.1f}/3000字），"
            f"直接情绪词约 {direct_hits} 次；检查是否用身体症状代替了全部情绪。"
        )
        findings.append(Finding("EMOTION_MIX", note))
    elif body_hits >= 3 and direct_hits == 0:
        findings.append(
            Finding(
                "EMOTION_MIX",
                f"身体化情绪信号 {body_hits} 次，但未发现常见直接情绪词；抽查是否过度执行 show-don't-tell。",
            )
        )

    closure_hits = count_regexes(text, CLOSURE_PATTERNS)
    if closure_hits >= 3:
        findings.append(
            Finding(
                "THEME_CLOSURE",
                f"总结/意义揭晓信号 {closure_hits} 次；检查动作或对白已经成立后是否又替读者下结论。",
            )
        )

    causal_hits = sum(text.count(word) for word in CAUSAL_WORDS)
    causal_rate = causal_hits * 3000 / char_count
    if causal_hits >= 12 and causal_rate >= 7.0:
        findings.append(
            Finding(
                "CAUSAL_TEXTURE",
                f"显式因果/顺序连接词 {causal_hits} 次（约 {causal_rate:.1f}/3000字）；检查是否形成流程图式推进。",
            )
        )

    quotes = QUOTE_RE.findall(text)
    abstract_quote_hits = sum(
        sum(quote.count(word) for word in DIALOGUE_ABSTRACT_WORDS) for quote in quotes
    )
    if len(quotes) >= 6 and abstract_quote_hits >= 5:
        findings.append(
            Finding(
                "DIALOGUE_PURPOSE",
                f"对白中主题/抽象词命中 {abstract_quote_hits} 次；逐句问“这个人为什么现在必须说这句话？”。",
            )
        )

    short_closure_paragraphs = 0
    for paragraph in paragraphs:
        compact = re.sub(r"\s+", "", paragraph)
        if len(compact) <= 70 and count_regexes(compact, CLOSURE_PATTERNS):
            short_closure_paragraphs += 1
    if short_closure_paragraphs >= 2:
        findings.append(
            Finding(
                "PARAGRAPH_CLOSURE",
                f"发现 {short_closure_paragraphs} 个较短的总结式段落；检查是否每个段落都被强行收尾。",
            )
        )

    outline_sample = [first_sentence(p) for p in paragraphs[:12]]
    outline_sample = [s for s in outline_sample if s]
    return findings, outline_sample


def review_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR {path}: {exc}", file=sys.stderr)
        return False

    findings, outline_sample = review_text(text)
    print(f"\nNARRATIVE REVIEW: {path}")
    if findings:
        for finding in findings:
            print(f"REVIEW [{finding.label}] {finding.detail}")
    else:
        print("No heuristic narrative-density warning crossed the V1 review threshold.")

    if outline_sample:
        print("PARAGRAPH-FIRST-SENTENCE SAMPLE (manual QUD/outline check):")
        for index, sentence in enumerate(outline_sample, start=1):
            print(f"  {index:02d}. {sentence}")

    print(
        "Manual checks still required: Architecture Lite, scene QUD, reveal pacing, "
        "non-instrumental scene texture, dialogue immediate purpose, and calibration."
    )
    return True


def main() -> int:
    args = parse_args()
    ok = True
    for path in args.files:
        ok = review_file(path) and ok

    if not ok:
        return 2

    print(
        "\nNARRATIVE GUARD: REVIEW COMPLETE (advisory V1; findings do not auto-fail the chapter)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
