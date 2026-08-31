#!/usr/bin/env python3
"""Run all mandatory fiction quality guards in one command.

Usage:
    python shared/tools/novel_gate.py chapter-001.md [chapter-002.md ...]

The wrapper does not rewrite text. It runs the repository's narrative,
dialogue, humanizer, prose, and meta-narrative guards in sequence so agents
are less likely to skip one layer.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
GUARDS = (
    "narrative_guard.py",
    "dialogue_guard.py",
    "humanizer_guard.py",
    "prose_guard.py",
    "meta_narrative_guard.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all novel-workspace fiction quality guards.")
    parser.add_argument("files", nargs="+", type=Path, help="UTF-8 chapter markdown/text files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = [str(path) for path in args.files]
    failures: list[tuple[str, int]] = []

    for guard_name in GUARDS:
        guard_path = HERE / guard_name
        if not guard_path.exists():
            print(f"ERROR missing guard: {guard_path}", file=sys.stderr)
            failures.append((guard_name, 1))
            continue

        print("\n" + "=" * 72)
        print(f"RUN {guard_name}")
        print("=" * 72)
        completed = subprocess.run([sys.executable, str(guard_path), *files], check=False)
        if completed.returncode != 0:
            failures.append((guard_name, completed.returncode))

    print("\n" + "=" * 72)
    if failures:
        print("NOVEL GATE: REVIEW REQUIRED")
        for name, code in failures:
            print(f"- {name}: exit {code}")
        print(
            "A non-zero guard result does not mean auto-rewrite. Review every hit against "
            "the relevant rule files, preserve continuity/numbers, then rerun."
        )
        return 2

    print("NOVEL GATE: AUTOMATED GUARDS COMPLETED")
    print(
        "Automated success is not final approval. Manual Architecture Lite / QUD, "
        "Dialogue/Humanizer/Prose review, voice-sample comparison, continuity, number "
        "checks, and final read are still required. narrative_guard.py is advisory in V1."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
