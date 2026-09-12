from __future__ import annotations

import argparse
import difflib
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "chapters"
CHAPTER_RE = re.compile(r"chapter-(\d+)\.md$")
CLEAN_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")


def normalize(text: str) -> str:
    return CLEAN_RE.sub("", text)


def chapter_no(path: Path) -> int:
    match = CHAPTER_RE.search(path.name)
    if not match:
        raise ValueError(path)
    return int(match.group(1))


def paragraphs(path: Path) -> list[tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    raw_paragraphs = re.split(r"\n\s*\n", text)
    out: list[tuple[int, str, str]] = []
    for index, raw in enumerate(raw_paragraphs, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("# "):
            continue
        if stripped.startswith("【") and stripped.endswith("】"):
            continue
        norm = normalize(stripped)
        if len(norm) < 80:
            continue
        out.append((index, stripped, norm))
    return out


def snippet(text: str, limit: int = 72) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=9999)
    parser.add_argument("--exact-min", type=int, default=100)
    parser.add_argument("--near-min", type=int, default=140)
    parser.add_argument("--near-threshold", type=float, default=0.92)
    args = parser.parse_args()

    files = sorted(
        (
            path
            for path in CHAPTER_DIR.glob("chapter-*.md")
            if args.start <= chapter_no(path) <= args.end
        ),
        key=chapter_no,
    )

    entries: list[tuple[int, int, str, str]] = []
    for path in files:
        no = chapter_no(path)
        for p_index, raw, norm in paragraphs(path):
            entries.append((no, p_index, raw, norm))

    failures: list[str] = []

    # Exact long-paragraph duplicates across different chapters.
    exact: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for no, p_index, raw, norm in entries:
        if len(norm) >= args.exact_min:
            exact[norm].append((no, p_index, raw))
    for matches in exact.values():
        chapter_ids = {item[0] for item in matches}
        if len(chapter_ids) < 2:
            continue
        rendered = ", ".join(f"ch{no}:p{p_index}" for no, p_index, _ in matches)
        failures.append(
            f"EXACT_REPEAT {rendered} | {snippet(matches[0][2])}"
        )

    # Near-duplicate long paragraphs. Prefix bucketing keeps this inexpensive and
    # specifically catches templated paragraphs with small noun/place substitutions.
    buckets: dict[str, list[tuple[int, int, str, str]]] = defaultdict(list)
    for entry in entries:
        no, p_index, raw, norm = entry
        if len(norm) < args.near_min:
            continue
        buckets[norm[:10]].append(entry)

    seen_pairs: set[tuple[int, int, int, int]] = set()
    for bucket in buckets.values():
        for i in range(len(bucket)):
            no_a, p_a, raw_a, norm_a = bucket[i]
            for j in range(i + 1, len(bucket)):
                no_b, p_b, raw_b, norm_b = bucket[j]
                if no_a == no_b:
                    continue
                key = (no_a, p_a, no_b, p_b)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                ratio = min(len(norm_a), len(norm_b)) / max(len(norm_a), len(norm_b))
                if ratio < 0.82:
                    continue
                similarity = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
                if similarity >= args.near_threshold:
                    failures.append(
                        "NEAR_REPEAT "
                        f"ch{no_a}:p{p_a} <-> ch{no_b}:p{p_b} "
                        f"similarity={similarity:.3f} | {snippet(raw_a)}"
                    )

    if failures:
        print(f"Cross-chapter repetition guard failed: {len(failures)} finding(s).")
        for failure in failures:
            print(failure)
        return 1

    print(
        f"Cross-chapter repetition guard passed: chapters {args.start}-{args.end}, "
        f"{len(entries)} long narrative paragraph(s) checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
