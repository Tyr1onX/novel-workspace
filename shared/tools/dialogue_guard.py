#!/usr/bin/env python3
"""Heuristic dialogue guard for Chinese novel drafts.

This tool locates dialogue structures that often read as generated rather than
lived-in: long short-turn ping-pong runs, interview-like question chains,
minimal-answer ladders, repeated functional prompts, and dialogue-heavy blocks
with little scene interruption.

It NEVER rewrites text and its warnings are not proof that a passage is bad.
Human review against shared/DIALOGUE_RULES.md is mandatory.

Exit codes:
  0: scan completed
  1: usage/file error
"""

from __future__ import annotations

import argparse
import collections
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PURE_DIALOGUE_RE = re.compile(r"^[\s>*-]*[“‘].*[”’][\s]*$")
QUOTED_RE = re.compile(r"[“‘](.*?)[”’]")
QUESTION_RE = re.compile(r"[？?]\s*$")

# Very short replies are normal in isolation. The tool only warns when several
# of them participate in a larger mechanically alternating run.
MINIMAL_REPLIES = {
    "嗯", "嗯。", "对", "对。", "行", "行。", "好", "好。", "是", "是。",
    "不是", "不是。", "知道", "知道。", "没有", "没有。", "不知道", "不知道。",
    "差不多", "差不多。", "还行", "还行。", "可以", "可以。", "真的", "真的。",
}

# Project-agnostic phrases that often become author-facing information prompts
# when they recur. They are WARN-only and must be judged in context.
FUNCTION_PROMPTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("THEN_WHAT", re.compile(r"^(?:然后呢|后来呢|那然后呢)[？?]?$")),
    ("HOW_MANY", re.compile(r"^(?:多少|多少步|多少钱|多远|几点|多久)[了呢？?。]*$")),
    ("YOU_MEAN", re.compile(r"^(?:所以你的意思是|也就是说|那你的意思是)")),
    ("STILL_GO", re.compile(r"(?:还走|又走|继续走|走回去|走过去).*[？?]$")),
)


@dataclass
class DialogueTurn:
    line_no: int
    text: str
    pure: bool

    @property
    def question(self) -> bool:
        return bool(QUESTION_RE.search(self.text.rstrip()))

    @property
    def short(self) -> bool:
        return len(self.text.strip("“”‘’ \t")) <= 12

    @property
    def minimal(self) -> bool:
        return self.text.strip("“”‘’ \t") in MINIMAL_REPLIES


def extract_turn(line_no: int, raw: str) -> DialogueTurn | None:
    matches = QUOTED_RE.findall(raw)
    if not matches:
        return None
    # A line may contain narration plus one quotation; use the first spoken span
    # for structural heuristics and preserve whether the entire line is dialogue.
    spoken = matches[0].strip()
    return DialogueTurn(line_no, spoken, bool(PURE_DIALOGUE_RE.match(raw.strip())))


def contiguous_runs(turns: list[DialogueTurn], max_gap: int = 1) -> list[list[DialogueTurn]]:
    if not turns:
        return []
    runs: list[list[DialogueTurn]] = []
    current = [turns[0]]
    for turn in turns[1:]:
        if turn.line_no - current[-1].line_no <= max_gap + 1:
            current.append(turn)
        else:
            runs.append(current)
            current = [turn]
    runs.append(current)
    return runs


def human_range(run: Iterable[DialogueTurn]) -> str:
    seq = list(run)
    return f"{seq[0].line_no}-{seq[-1].line_no}"


def scan_file(path: Path) -> dict[str, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR {path}: {exc}")
        raise

    lines = text.splitlines()
    turns = [t for i, line in enumerate(lines, 1) if (t := extract_turn(i, line))]
    pure_turns = [t for t in turns if t.pure]
    counts = collections.Counter()

    # 1. Long uninterrupted pure-dialogue runs.
    for run in contiguous_runs(pure_turns, max_gap=1):
        if len(run) < 6:
            continue
        short_ratio = sum(t.short for t in run) / len(run)
        question_ratio = sum(t.question for t in run) / len(run)
        minimal_count = sum(t.minimal for t in run)

        if short_ratio >= 0.70:
            counts["SHORT_PINGPONG"] += 1
            print(
                f"WARN {path}:{human_range(run)} SHORT_PINGPONG: "
                f"连续{len(run)}轮纯对白，{short_ratio:.0%}为短句；人工检查是否完美接球"
            )

        if question_ratio >= 0.45 and len(run) >= 6:
            counts["QUESTION_CHAIN"] += 1
            print(
                f"WARN {path}:{human_range(run)} QUESTION_CHAIN: "
                f"连续对白中问句占{question_ratio:.0%}；检查是否采访/审讯式输送信息"
            )

        if minimal_count >= 2 and len(run) >= 5:
            counts["MINIMAL_LADDER"] += 1
            print(
                f"WARN {path}:{human_range(run)} MINIMAL_LADDER: "
                f"同一连续对白含{minimal_count}个极短回答；检查是否“问一句—答一句”阶梯"
            )

    # 2. Consecutive questions even if narration is interleaved lightly.
    for run in contiguous_runs(turns, max_gap=2):
        if len(run) < 5:
            continue
        questions = sum(t.question for t in run)
        if questions >= 4 and questions / len(run) >= 0.55:
            counts["INTERVIEW_BLOCK"] += 1
            print(
                f"WARN {path}:{human_range(run)} INTERVIEW_BLOCK: "
                f"{len(run)}个对白回合中{questions}个问句；检查角色是否只在替作者追问信息"
            )

    # 3. Repeated functional prompt forms inside one chapter.
    prompt_hits: dict[str, list[int]] = collections.defaultdict(list)
    for t in turns:
        normalized = t.text.strip()
        for code, pattern in FUNCTION_PROMPTS:
            if pattern.search(normalized):
                prompt_hits[code].append(t.line_no)

    for code, line_nos in prompt_hits.items():
        if len(line_nos) >= 2:
            counts[f"REPEATED_{code}"] += 1
            print(
                f"WARN {path}:{','.join(map(str, line_nos))} REPEATED_{code}: "
                f"同章重复{len(line_nos)}次同类功能问句；检查人物是否被固定成提问器"
            )

    # 4. Dialogue density: not an error, only a locator for manual sampling.
    nonblank = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if nonblank:
        quote_lines = sum(bool(QUOTED_RE.search(ln)) for ln in nonblank)
        ratio = quote_lines / len(nonblank)
        if ratio >= 0.48 and quote_lines >= 18:
            counts["DIALOGUE_DENSITY"] += 1
            print(
                f"INFO {path} DIALOGUE_DENSITY: 对白行占非空正文{ratio:.0%} "
                f"({quote_lines}/{len(nonblank)})；抽样做遮名字测试"
            )

    print(
        f"SUMMARY {path}: turns={len(turns)} "
        + " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    )
    return dict(counts)


def cross_file_report(files: list[Path]) -> None:
    """Report repeated exact/similar short questions across a batch of chapters."""
    phrase_locations: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    semantic_buckets: dict[str, list[tuple[str, int, str]]] = collections.defaultdict(list)

    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for i, line in enumerate(lines, 1):
            turn = extract_turn(i, line)
            if not turn or not turn.question:
                continue
            normalized = re.sub(r"[\s？?。！!]", "", turn.text)
            if 2 <= len(normalized) <= 14:
                phrase_locations[normalized].append((str(path), i))
            for code, pattern in FUNCTION_PROMPTS:
                if pattern.search(turn.text.strip()):
                    semantic_buckets[code].append((str(path), i, turn.text.strip()))

    print("\n=== CROSS-FILE DIALOGUE REPORT ===")
    repeated = sorted(
        ((phrase, locs) for phrase, locs in phrase_locations.items() if len(locs) >= 3),
        key=lambda x: (-len(x[1]), x[0]),
    )
    for phrase, locs in repeated[:30]:
        where = ", ".join(f"{Path(p).name}:{ln}" for p, ln in locs[:8])
        suffix = " ..." if len(locs) > 8 else ""
        print(f"WARN REPEATED_EXACT_QUESTION x{len(locs)} “{phrase}”: {where}{suffix}")

    for code, locs in semantic_buckets.items():
        chapter_names = {Path(p).name for p, _, _ in locs}
        if len(locs) >= 4 and len(chapter_names) >= 3:
            sample = "; ".join(f"{Path(p).name}:{ln} {txt}" for p, ln, txt in locs[:6])
            print(
                f"WARN CROSS_{code}: {len(locs)} hits across {len(chapter_names)} chapters; "
                f"check repeated character/function pattern. {sample}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Locate high-risk generated-dialogue structures in Chinese novel drafts."
    )
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 markdown/text files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failed = False
    for path in args.files:
        try:
            scan_file(path)
        except (OSError, UnicodeError):
            failed = True
    if len(args.files) > 1:
        cross_file_report(args.files)
    print("Gate: warnings require human Dialogue Pass; this tool never auto-approves prose.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
