#!/usr/bin/env python3
"""Heuristic Humanizer guard for Chinese fiction.

The guard locates common AI-writing structures adapted from public humanizer
projects and this repository's HUMANIZER_RULES.md. It never rewrites prose and
never proves that a passage is AI-generated. Every hit requires human review.

Exit codes:
  0: scan completed and no HARD pattern was found
  1: usage/file error or at least one HARD pattern was found
"""

from __future__ import annotations

import argparse
import collections
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


PURE_DIALOGUE_RE = re.compile(r"^[\s>*-]*[“‘].*[”’][\s]*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])")

# These are almost always essay/chatbot residue when they appear in narrative
# prose. Quoted dialogue is downgraded to WARN because a character may actually
# speak that way.
HARD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("STOCK_CONCLUSION", re.compile(r"(?:综上所述|总而言之|总的来说|综合以上|在未来的道路上|让我们共同|让我们一起迈向)")),
    ("FORMULAIC_OPENING", re.compile(r"(?:在当今.{0,10}(?:时代|背景下)|在这个.{0,10}(?:时代|社会)|随着.{0,12}(?:快速发展|不断发展)|在.{0,10}浪潮下)")),
    ("ANNOUNCE_NEXT", re.compile(r"(?:话不多说|废话不多说|接下来(?:就|让我们)?(?:来|一起)?(?:看看|看|了解|拆解)|让我们(?:一起)?来看看|下面(?:就|让我们)?来看看)")),
)

WARN_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("DEEP_TRUTH", re.compile(r"(?:真正的问题是|真正重要的是|本质上|归根结底|核心在于|更深层|说到底|心底真正|真正的答案)"), "检查是否把普通事实包装成隐藏真相"),
    ("FAKE_ALTERNATIVE", re.compile(r"(?:你可能以为|看似.{0,18}(?:其实|实则)|表面上.{0,18}(?:其实|真正)|与其说.{0,20}不如说)"), "检查前半个选项是否真实成立"),
    ("NOT_X_BUT_Y", re.compile(r"(?:不是.{1,28}(?:而是|是)|并非.{1,28}(?:而是|而在于)|不在于.{1,28}而在于|不仅仅是.{1,28}(?:更是|而是)|不仅.{1,22}(?:还|更))"), "检查是否为生成式翻案/二元对举"),
    ("EXPLANATION_TAIL", re.compile(r"(?:这意味着|这说明|这也意味着|他这才(?:意识到|明白|懂得)|她这才(?:意识到|明白|懂得)|某种变化正在|这一刻他才|这一刻她才)"), "动作或结果之后可能又解释了一遍"),
    ("FAKE_CANDID", re.compile(r"(?:说实话|老实说|讲真的|不得不承认|坦白说)"), "检查是否用假坦白给普通判断抬价"),
    ("FILLER", re.compile(r"(?:值得注意的是|值得一提的是|事实上|从某种意义上说|某种程度上|可以说|不难发现|显而易见的是)"), "检查是否是可直接删除的填充/缓冲"),
    ("ABSTRACT_FEELING", re.compile(r"(?:难以言喻|说不出的|一股复杂的情绪|一种复杂的情绪|某种复杂的|前所未有的感觉|莫名的情绪)"), "检查是否用抽象情绪代替现场"),
    ("GENERIC_POSITIVE", re.compile(r"(?:新的生活才刚刚开始|未来(?:仍|还)?(?:充满|有着).{0,8}(?:可能|希望)|一切都在(?:悄然)?改变|一切都会好起来)"), "检查是否为无新事实的积极收尾"),
    ("AI_CONNECTOR", re.compile(r"^(?:此外|与此同时|因此|然而|其次|再者|最后|首先)[，,]"), "高密度连接词会形成说明文/模型路标感"),
    ("MEANING_VERB", re.compile(r"(?:彰显了|体现了|展现了|凸显了|印证了|证明了).{0,20}(?:意义|重要|变化|成长|价值|决心|态度)"), "检查是否给普通动作追加意义"),
)

AI_TICS = (
    "终于", "真正", "甚至", "似乎", "某种", "意味着", "意识到", "明白",
    "悄然", "逐渐", "仿佛", "这一刻", "那一刻", "第一次",
)


@dataclass
class Hit:
    severity: str
    code: str
    line_no: int
    text: str
    note: str


def is_pure_dialogue(line: str) -> bool:
    return bool(PURE_DIALOGUE_RE.match(line.strip()))


def visible_len(sentence: str) -> int:
    return len(re.sub(r"[\s#>*`_\-—–，。！？!?；;：:、“”‘’（）()]", "", sentence))


def sentences_from_line(line: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(line) if s.strip()]


def scan_patterns(path: Path, lines: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        dialogue = is_pure_dialogue(line)

        for code, pattern in HARD_PATTERNS:
            if pattern.search(line):
                severity = "WARN" if dialogue else "HARD"
                hits.append(Hit(severity, code, i, line, "公式化文章/聊天机器人残留"))

        for code, pattern, note in WARN_PATTERNS:
            if pattern.search(line):
                hits.append(Hit("WARN", code, i, line, note))

        # Short aphorism shape: very weak heuristic, WARN only.
        for sentence in sentences_from_line(line):
            clean = sentence.strip("“”‘’ ")
            if 8 <= visible_len(clean) <= 30:
                if re.search(r"^.{2,10}是.{2,10}的.{2,10}[。！!]?$", clean):
                    hits.append(
                        Hit("WARN", "APHORISM_SHAPE", i, sentence, "短句呈‘X是Y的Z’金句外形；检查是否脱离现场仍像海报句")
                    )
                    break
    return hits


def scan_short_paragraph_runs(path: Path, lines: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    run: list[tuple[int, str]] = []

    def flush() -> None:
        nonlocal run
        if len(run) >= 4:
            hits.append(
                Hit(
                    "WARN",
                    "DRAMATIC_SHORT_RUN",
                    run[0][0],
                    " / ".join(text for _, text in run[:5]),
                    f"连续{len(run)}个短叙述段；检查是否每句都在抢重音",
                )
            )
        run = []

    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            flush()
            continue
        if is_pure_dialogue(line) or "【" in line or "】" in line:
            flush()
            continue
        # Single-sentence short narrative paragraph.
        sentence_count = len([s for s in sentences_from_line(line) if s])
        if sentence_count == 1 and visible_len(line) <= 16:
            run.append((i, line))
        else:
            flush()
    flush()
    return hits


def scan_uniform_sentences(path: Path, lines: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    seq: list[tuple[int, str, int]] = []

    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#") or is_pure_dialogue(line) or "【" in line:
            continue
        for sentence in sentences_from_line(line):
            n = visible_len(sentence)
            if 8 <= n <= 60:
                seq.append((i, sentence, n))

    for idx in range(len(seq) - 3):
        window = seq[idx : idx + 4]
        lens = [x[2] for x in window]
        avg = mean(lens)
        if avg < 10:
            continue
        spread = max(lens) - min(lens)
        if spread <= max(3, avg * 0.18):
            # Avoid printing heavily overlapping windows.
            if hits and hits[-1].code == "UNIFORM_SENTENCE_LENGTH" and window[0][0] <= hits[-1].line_no + 2:
                continue
            sample = " | ".join(x[1] for x in window)
            hits.append(
                Hit(
                    "WARN",
                    "UNIFORM_SENTENCE_LENGTH",
                    window[0][0],
                    sample,
                    f"连续4句长度过匀 {lens}；检查是否被同一节拍抛光",
                )
            )
    return hits


def scan_tic_density(path: Path, text: str) -> list[Hit]:
    hits: list[Hit] = []
    for tic in AI_TICS:
        count = text.count(tic)
        # Chapter-level threshold is intentionally loose. These are not banned.
        if count >= 5:
            hits.append(
                Hit(
                    "WARN",
                    "TIC_DENSITY",
                    0,
                    tic,
                    f"‘{tic}’本章出现{count}次；不要换同义词，先检查句子是否都需要",
                )
            )
    return hits


def scan_file(path: Path) -> tuple[int, int, collections.Counter[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR {path}: {exc}")
        raise

    lines = text.splitlines()
    hits = []
    hits.extend(scan_patterns(path, lines))
    hits.extend(scan_short_paragraph_runs(path, lines))
    hits.extend(scan_uniform_sentences(path, lines))
    hits.extend(scan_tic_density(path, text))

    # Deduplicate exact same code/line/text.
    unique: list[Hit] = []
    seen: set[tuple[str, int, str]] = set()
    for hit in hits:
        key = (hit.code, hit.line_no, hit.text)
        if key not in seen:
            seen.add(key)
            unique.append(hit)

    unique.sort(key=lambda h: (0 if h.line_no else 10**9, h.line_no, h.severity, h.code))
    counts: collections.Counter[str] = collections.Counter()
    hard = warn = 0

    for hit in unique:
        counts[hit.code] += 1
        if hit.severity == "HARD":
            hard += 1
        else:
            warn += 1
        location = f":{hit.line_no}" if hit.line_no else ""
        excerpt = re.sub(r"\s+", " ", hit.text)
        if len(excerpt) > 120:
            excerpt = excerpt[:117] + "..."
        print(f"{hit.severity} {path}{location} {hit.code}: {hit.note} :: {excerpt}")

    print(
        f"SUMMARY {path}: HARD={hard} WARN={warn} "
        + " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    )
    return hard, warn, counts


def cross_file_report(files: list[Path]) -> None:
    """Locate recurring author/model tics across a batch of chapters."""
    tic_locations: dict[str, list[str]] = collections.defaultdict(list)
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for tic in AI_TICS:
            count = text.count(tic)
            if count:
                tic_locations[tic].append(f"{path.name}×{count}")

    print("\n=== CROSS-FILE HUMANIZER REPORT ===")
    for tic, locs in sorted(tic_locations.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(locs) >= 4:
            print(f"WARN CROSS_TIC ‘{tic}’: appears in {len(locs)} files; " + ", ".join(locs[:12]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Locate common AI-writing structures in Chinese fiction without rewriting them."
    )
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 markdown/text files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failed = False
    total_hard = 0
    for path in args.files:
        try:
            hard, _, _ = scan_file(path)
            total_hard += hard
        except (OSError, UnicodeError):
            failed = True

    if len(args.files) > 1:
        cross_file_report(args.files)

    print(
        "Gate: HARD must be 0. WARN requires manual Humanizer Pass against "
        "shared/HUMANIZER_RULES.md; warnings are not proof of AI authorship."
    )
    return 1 if failed or total_hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
