#!/usr/bin/env python3
"""Detect fourth-wall / writing-process leakage in novel prose.

The chapter title is allowed to contain its chapter number. Body prose is not.
This tool never rewrites text; it reports hard leaks and review warnings.

Exit codes:
  0: no hard leaks
  2: one or more hard leaks
  1: usage / file error
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    description: str
    pattern: re.Pattern[str]


CN_NUM = r"零〇一二三四五六七八九十百两\d"

RULES: tuple[Rule, ...] = (
    Rule(
        "CHAPTER_NUMBER_REF",
        "HARD",
        "正文引用章节编号",
        re.compile(rf"第[{CN_NUM}]{{1,6}}章"),
    ),
    Rule(
        "RELATIVE_CHAPTER_REF",
        "HARD",
        "正文引用上一章/下一章/本章等小说结构",
        re.compile(r"(?:上一|下一|前一|后一|这一|那一|本|上|下)(?:个)?章"),
    ),
    Rule(
        "VOLUME_REF",
        "HARD",
        "正文引用上一卷/下一卷/本卷等小说结构",
        re.compile(r"(?:上一|下一|前一|后一|这一|那一|本|上|下)(?:个)?卷"),
    ),
    Rule(
        "WRITING_LAYER_WORD",
        "HARD",
        "正文出现作者/读者/正文/剧情/章节/排章等写作层词",
        re.compile(r"作者|读者|正文|剧情|章节|排章"),
    ),
    Rule(
        "LONG_PLOT",
        "HARD",
        "正文把事件称作长剧情/剧情线",
        re.compile(r"长剧情|剧情线|主线剧情|支线剧情"),
    ),
    Rule(
        "WRITE_AS_PROCESS",
        "WARN",
        "疑似把世界内事件当作写作对象，请人工确认",
        re.compile(r"(?:写成|写得|写进).{0,16}(?:一章|章节|剧情|长试验|长过程|长流程)"),
    ),
    Rule(
        "AUTHORIAL_EXPANSION",
        "WARN",
        "疑似作者在决定是否展开过程，请人工确认",
        re.compile(r"(?:继续|再|没有再|没有继续).{0,10}(?:展开|复制).{0,12}(?:过程|试验|流程)?"),
    ),
)


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
        if in_fence or not stripped:
            continue
        # Markdown headings are metadata, not story-body prose.
        if stripped.startswith("#"):
            continue

        for rule in RULES:
            for match in rule.pattern.finditer(raw_line):
                if rule.severity == "HARD":
                    hard += 1
                else:
                    warn += 1
                snippet = raw_line.strip()
                print(
                    f"{rule.severity:<4} {path}:{line_no} {rule.code}: "
                    f"{rule.description}\n"
                    f"      ↳ {snippet}"
                )

    print(f"SUMMARY {path}: hard={hard} warn={warn}")
    return hard, warn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect meta-narrative leakage in novel body prose."
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
        print("Gate: meta-narrative leakage found; body prose must be repaired before merge.")
        return 2
    print("Gate: no hard meta-narrative leakage found. Review warnings manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
