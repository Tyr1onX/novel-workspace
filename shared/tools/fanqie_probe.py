#!/usr/bin/env python3
"""Read-only connectivity probe for the local Fanqie publisher runtime.

This helper never creates, edits, publishes, deletes, or reschedules chapters.
It only resolves the locally installed runtime and runs the upstream `books`
command to verify the saved login session can see the configured book.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


class ProbeError(RuntimeError):
    pass


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def _is_runtime(path: Path) -> bool:
    return (path / "fanqie_upload.py").is_file()


def resolve_runtime(explicit: str | None = None) -> Path:
    """Resolve the pinned publisher runtime without hard-coding a drive letter.

    Resolution order:
    1. explicit CLI path;
    2. FANQIE_RUNTIME_DIR environment variable;
    3. a `publisher` directory next to the self-hosted runner directory,
       inferred from RUNNER_TEMP (matches the recommended Workspace layout);
    4. the historical default under the user's home directory.
    """
    searched: list[Path] = []

    if explicit:
        path = _expand(explicit)
        if _is_runtime(path):
            return path
        raise ProbeError(f"explicit Fanqie runtime is invalid: {path}")

    env_value = os.environ.get("FANQIE_RUNTIME_DIR")
    if env_value:
        path = _expand(env_value)
        searched.append(path)
        if _is_runtime(path):
            return path

    runner_temp = os.environ.get("RUNNER_TEMP")
    if runner_temp:
        temp = _expand(runner_temp)
        # A self-hosted runner normally exposes RUNNER_TEMP as:
        #   <runner>/_work/_temp
        # Walk upward rather than relying on exactly two parents so this remains
        # resilient to small runner layout changes.
        for ancestor in (temp, *temp.parents):
            candidate = ancestor.parent / "publisher"
            if candidate in searched:
                continue
            searched.append(candidate)
            if _is_runtime(candidate):
                return candidate.resolve()

    default = Path.home() / ".novel-workspace" / "fanqie-publisher"
    searched.append(default)
    if _is_runtime(default):
        return default.resolve()

    locations = "\n  - ".join(str(p) for p in searched)
    raise ProbeError(
        "Fanqie publisher runtime was not found. Searched:\n  - " + locations
    )


def load_book_id(novel_dir: Path) -> str:
    config_path = novel_dir / "platform-sync" / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeError(f"cannot read {config_path}: {exc}") from exc
    book_id = str(config.get("book_id", "")).strip()
    if not book_id:
        raise ProbeError(f"missing book_id in {config_path}")
    return book_id


def output_contains_book_id(output: str, book_id: str) -> bool:
    # Upstream writes through the logger, so lines may be prefixed with a
    # timestamp and "[INFO]". Match the ID token anywhere on a line, while
    # still requiring a numeric boundary so a partial ID cannot pass.
    pattern = re.compile(rf"(?m)\bID:\s*{re.escape(book_id)}(?=\s|$)")
    return bool(pattern.search(output))


def probe(novel_dir: Path, runtime_arg: str | None = None) -> int:
    runtime = resolve_runtime(runtime_arg)
    book_id = load_book_id(novel_dir)
    script = runtime / "fanqie_upload.py"

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, str(script), "books"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = proc.stdout or ""
    print(output, end="" if output.endswith("\n") else "\n")

    if proc.returncode != 0:
        raise ProbeError(f"publisher `books` exited with code {proc.returncode}")
    if not output_contains_book_id(output, book_id):
        raise ProbeError(
            f"saved Fanqie session is reachable, but configured book_id {book_id} was not found"
        )

    print(f"PROBE_OK book_id={book_id} runtime={runtime}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Fanqie connectivity probe")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve-runtime")
    resolve.add_argument("--runtime")

    check = sub.add_parser("probe")
    check.add_argument("novel_dir", type=Path)
    check.add_argument("--runtime")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "resolve-runtime":
            print(resolve_runtime(args.runtime))
            return 0
        if args.command == "probe":
            return probe(args.novel_dir.resolve(), args.runtime)
    except ProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
