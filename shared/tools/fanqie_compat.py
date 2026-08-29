#!/usr/bin/env python3
"""Compatibility entrypoint for repository Fanqie tools.

Older novel projects use headings such as `# 第一章 标题` while newer projects use
`# 第1章 标题`. The canonical Markdown should not be rewritten merely for publishing,
so this entrypoint broadens local parsing before delegating to the existing sync,
reconciliation, and publish-now controllers.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
from pathlib import Path

import fanqie_sync


CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
HEADING_RE = re.compile(
    r"^#\s*第\s*([0-9]+|[零〇一二两三四五六七八九十百千]+)\s*[章回节话]\s*(.*?)\s*$"
)


def cn_to_int(text: str) -> int:
    if text.isdigit():
        return int(text)
    total = 0
    current = 0
    for ch in text:
        if ch in CN_DIGITS:
            current = CN_DIGITS[ch]
            continue
        unit = CN_UNITS.get(ch)
        if unit is None:
            raise fanqie_sync.SyncError(f"unsupported Chinese chapter number: {text}")
        if current == 0:
            current = 1
        total += current * unit
        current = 0
    return total + current


def parse_chapter_compat(path: Path) -> fanqie_sync.Chapter:
    file_match = fanqie_sync.CHAPTER_FILE_RE.search(path.name)
    if not file_match:
        raise fanqie_sync.SyncError(f"unsupported chapter filename: {path.name}")
    file_number = int(file_match.group(1))
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    heading_index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if heading_index is None:
        raise fanqie_sync.SyncError(f"empty chapter: {path}")
    heading = HEADING_RE.match(lines[heading_index].strip())
    if not heading:
        raise fanqie_sync.SyncError(
            f"first non-empty line is not '# 第N章 标题' or '# 第X章 标题': {path}"
        )
    heading_number = cn_to_int(heading.group(1))
    if heading_number != file_number:
        raise fanqie_sync.SyncError(
            f"chapter number mismatch in {path}: filename={file_number}, heading={heading_number}"
        )
    title = heading.group(2).strip()
    if not title:
        raise fanqie_sync.SyncError(f"empty chapter title: {path}")
    body = fanqie_sync.normalize_body(lines[heading_index + 1 :])
    if not body.strip():
        raise fanqie_sync.SyncError(f"empty chapter body: {path}")
    digest = hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()
    char_count = len(re.sub(r"\s", "", body))
    return fanqie_sync.Chapter(file_number, title, body, path, digest, char_count)


def install_compat() -> None:
    fanqie_sync.parse_chapter = parse_chapter_compat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compatibility entrypoint for Fanqie repository tools")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "plan", "sync"):
        p = sub.add_parser(name)
        p.add_argument("novel_dir", type=Path)
        if name == "plan":
            p.add_argument("--json", action="store_true")
        if name == "sync":
            p.add_argument("--runtime")
            p.add_argument("--dry-run", action="store_true")

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("novel_dir", type=Path)
    reconcile.add_argument("--runtime")
    reconcile.add_argument("--output", type=Path)

    publish_now = sub.add_parser("publish-now")
    publish_now.add_argument("novel_dir", type=Path)
    publish_now.add_argument("--runtime")
    publish_now.add_argument("--request", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    install_compat()
    novel_dir = args.novel_dir.resolve()
    try:
        if args.command == "validate":
            return fanqie_sync.cmd_validate(novel_dir)
        if args.command == "plan":
            return fanqie_sync.cmd_plan(novel_dir, args.json)
        if args.command == "sync":
            return fanqie_sync.cmd_sync(novel_dir, args.runtime, args.dry_run)
        if args.command == "reconcile":
            import fanqie_reconcile
            return asyncio.run(fanqie_reconcile.run(novel_dir, args.runtime, args.output))
        if args.command == "publish-now":
            import fanqie_publish_now
            return asyncio.run(
                fanqie_publish_now.run(novel_dir, args.runtime, args.request.resolve())
            )
    except (fanqie_sync.SyncError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
