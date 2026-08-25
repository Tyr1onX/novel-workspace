#!/usr/bin/env python3
"""Lightweight prose guard for Chinese novel drafts.

This tool only locates high-risk AI-tone patterns described in
shared/PROSE_RULES.md. It never rewrites text.

Exit codes:
  0: no hard-review hits
  2: one or more hard-review hits were found
  1: usage / file error
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    description: str
    pattern: re.Pattern[str]


RULES: tuple[Rule, ...] = (
    Rule(
        "FLIP_NOT_BUT",
        "HARD",
        "否定—修正/翻案腔：先否定 A 再抬高 B",
        re.compile(r"不是.{0,40}?(?:而是|，是|。是|才是)"),
    ),
    Rule(
        "FLIP_NOT_BUT_2",
        "HARD",
        "否定—修正/翻案腔：并非 A 而是 B",
        re.compile(r"并非.{0,40}?而是"),
    ),
    Rule(
        "FLIP_LOCUS",
        "HARD",
        "翻案腔：不在于 A 而在于 B",
        re.compile(r"不在于.{0,40}?而在于"),
    ),
    Rule(
        "FLIP_RATHER",
        "HARD",
        "翻案腔：与其说 A 不如/倒不如/毋宁 B",
        re.compile(r"与其说.{0,50}?(?:不如说|倒不如|毋宁)"),
    ),
    Rule(
        "FLIP_SEEMS",
        "HARD",
        "翻案腔：看似/表面 A，实则/其实/真正 B",
        re.compile(r"(?:看似|表面(?:上)?).{0,50}?(?:实则|其实|真正)"),
    ),
    Rule(
        "FLIP_YOU_THINK",
        "HARD",
        "翻案腔：你以为 A，其实 B",
        re.compile(r"你以为.{0,50}?其实"),
    ),
    Rule(
        "EXPLAINER_CLOSER",
        "HARD",
        "解释式/升华式收束，检查是否在替场景总结主题",
        re.compile(r"这便是|如此.{0,6}?便|便已足够|这就是.{0,16}?(?:方式|意义|答案|代价|成长)"),
    ),
    Rule(
        "TRIPLE_NO",
        "HARD",
        "三拍否定排比，检查是否为生成式节拍",
        re.compile(r"没有[^。！？\n]{0,28}没有[^。！？\n]{0,28}没有"),
    ),
    Rule(
        "ABSTRACT_EMOTION",
        "WARN",
        "抽象情绪概括，检查是否替代了动作/现场",
        re.compile(r"难以言喻|说不出的|无尽的|莫名的|某种[^，。！？\n]{0,10}(?:情绪|感觉|意味)|一股[^，。！？\n]{0,10}(?:情绪|感觉)"),
    ),
    Rule(
        "MODEL_TIC",
        "WARN",
        "高频生成式口头禅，需结合章节密度判断",
        re.compile(r"终于|那一刻|这一刻|第一次|头一次|仿佛|意味着|意识到|真正明白|终于明白|终于懂得"),
    ),
    Rule(
        "PSEUDO_PAUSE",
        "WARN",
        "破折号停顿，检查是否只用于抬高普通判断",
        re.compile(r"——"),
    ),
    Rule(
        "PROMPT_COLON",
        "WARN",
        "提示语冒号，检查是否在替普通内容制造揭晓感",
        re.compile(r"(?:核心是|关键是|关键在于|答案是|真正的问题是|原因是|结论是)[:：]"),
    ),
)


QUOTE_PAIRS = (("“", "”"), ("‘", "’"))


def dialogue_ranges(line: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for left, right in QUOTE_PAIRS:
        pos = 0
        while True:
            start = line.find(left, pos)
            if start < 0:
                break
            end = line.find(right, start + 1)
            if end < 0:
                break
            ranges.append((start, end + 1))
            pos = end + 1
    return ranges


def inside_dialogue(start: int, end: int, ranges: Iterable[tuple[int, int]]) -> bool:
    return any(start >= qstart and end <= qend for qstart, qend in ranges)


def iter_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。！？!?]+", text) if s.strip()]


def repeated_starter_warnings(text: str) -> list[tuple[int, str]]:
    """Flag three adjacent similarly-sized sentences starting the same way.

    This is deliberately only a warning. It is a coarse locator for the
    'same skeleton / same beat' problem and must never auto-trigger rewrites.
    """
    sentences = iter_sentences(text)
    warnings: list[tuple[int, str]] = []
    cursor = 0

    for i in range(len(sentences) - 2):
        group = sentences[i : i + 3]
        starters = [re.sub(r"^[\s\"'“”‘’]+", "", s)[:2] for s in group]
        lengths = [len(s) for s in group]
        if not all(starters) or len(set(starters)) != 1:
            continue
        shortest = min(lengths)
        longest = max(lengths)
        if shortest == 0 or longest / shortest > 1.6:
            continue
        needle = group[0]
        pos = text.find(needle, cursor)
        if pos < 0:
            pos = 0
        line_no = text.count("\n", 0, pos) + 1
        cursor = pos + len(needle)
        warnings.append((line_no, starters[0]))

    return warnings


def scan_file(path: Path) -> tuple[int, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR {path}: {exc}", file=sys.stderr)
        return -1, -1

    hard = 0
    warn = 0
    in_fence = False

    for line_no, raw_line in enumerate(text.splitlines(), 1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith("#"):
            continue

        q_ranges = dialogue_ranges(raw_line)
        for rule in RULES:
            for match in rule.pattern.finditer(raw_line):
                severity = rule.severity
                note = ""
                if inside_dialogue(match.start(), match.end(), q_ranges):
                    # Direct speech may contain genuine correction or character tics.
                    severity = "WARN"
                    note = " [对白内：只检查是否符合人物与语境]"

                if severity == "HARD":
                    hard += 1
                else:
                    warn += 1

                snippet = match.group(0).strip()
                print(
                    f"{severity:<4} {path}:{line_no} {rule.code}: "
                    f"{rule.description}{note}\n"
                    f"      ↳ {snippet}"
                )

    for line_no, starter in repeated_starter_warnings(text):
        warn += 1
        print(
            f"WARN {path}:{line_no} REPEATED_START: "
            f"连续三句以“{starter}”开头且长度接近；人工检查是否同构/三拍"
        )

    print(f"SUMMARY {path}: hard={hard} warn={warn}")
    return hard, warn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Locate high-risk AI-tone patterns in Chinese novel drafts."
    )
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 markdown/text files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total_hard = 0
    total_warn = 0

    for path in args.files:
        hard, warn = scan_file(path)
        if hard < 0:
            return 1
        total_hard += hard
        total_warn += warn

    print(f"TOTAL hard={total_hard} warn={total_warn}")
    if total_hard:
        print("Gate: manual review required before the chapter is considered prose-clean.")
        return 2
    print("Gate: no hard-review pattern found. Warnings still require human judgment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
