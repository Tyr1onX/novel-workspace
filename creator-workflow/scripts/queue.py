#!/usr/bin/env python3
"""Creator workflow queue helpers.

This script intentionally stays small:
- validate CSV ledgers
- list due scheduled rows

It does not publish to any platform. Real publishing should be added only
after the platform permission and credential flow is confirmed.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

POSTS_CSV = DATA_DIR / "posts.csv"
DOUYIN_CSV = DATA_DIR / "douyin_posts.csv"

POST_COLUMNS = [
    "id",
    "platform",
    "account",
    "title",
    "type",
    "status",
    "scheduled_at",
    "published_at",
    "archive_path",
    "source_file",
    "notes",
]

DOUYIN_COLUMNS = [
    "id",
    "account",
    "title",
    "video_path",
    "cover_path",
    "caption",
    "hashtags",
    "scheduled_at",
    "published_at",
    "status",
    "douyin_item_id",
    "play_count",
    "like_count",
    "comment_count",
    "share_count",
    "notes",
]

ALLOWED_STATUS = {
    "idea",
    "draft",
    "ready",
    "scheduled",
    "published",
    "archived",
    "failed",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_time(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_table(path: Path, required_columns: list[str]) -> list[str]:
    errors: list[str] = []

    if not path.exists():
        return [f"missing file: {path.relative_to(ROOT)}"]

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        rows = list(reader)

    missing = [column for column in required_columns if column not in columns]
    if missing:
        errors.append(f"{path.relative_to(ROOT)} missing columns: {', '.join(missing)}")

    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        row_id = (row.get("id") or "").strip()
        status = (row.get("status") or "").strip()
        archive_path = (row.get("archive_path") or "").strip()
        scheduled_at = (row.get("scheduled_at") or "").strip()

        if not row_id:
            errors.append(f"{path.relative_to(ROOT)}:{index} missing id")
        elif row_id in seen_ids:
            errors.append(f"{path.relative_to(ROOT)}:{index} duplicate id: {row_id}")
        else:
            seen_ids.add(row_id)

        if status and status not in ALLOWED_STATUS:
            errors.append(f"{path.relative_to(ROOT)}:{index} invalid status: {status}")

        if scheduled_at:
            try:
                parse_time(scheduled_at)
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)}:{index} invalid scheduled_at: {scheduled_at}")

        if archive_path and not (ROOT.parent / archive_path).exists():
            errors.append(f"{path.relative_to(ROOT)}:{index} missing archive_path: {archive_path}")

    return errors


def due_rows(rows: Iterable[dict[str, str]], *, now: datetime, platform: str | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for row in rows:
        if platform and (row.get("platform") or "douyin") != platform:
            continue

        if (row.get("status") or "").strip() not in {"ready", "scheduled"}:
            continue

        scheduled_at = parse_time(row.get("scheduled_at") or "")
        if scheduled_at and scheduled_at <= now:
            result.append(row)

    return result


def command_validate(_: argparse.Namespace) -> int:
    errors = []
    errors.extend(validate_table(POSTS_CSV, POST_COLUMNS))
    errors.extend(validate_table(DOUYIN_CSV, DOUYIN_COLUMNS))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("creator-workflow validation passed")
    return 0


def command_due(args: argparse.Namespace) -> int:
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    rows = read_rows(POSTS_CSV)

    if args.platform in {None, "douyin"}:
        for row in read_rows(DOUYIN_CSV):
            row.setdefault("platform", "douyin")
            row.setdefault("type", "video")
            rows.append(row)

    result = due_rows(rows, now=now, platform=args.platform)
    print(json.dumps(result[: args.limit], ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Creator workflow queue helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate CSV ledgers")
    validate.set_defaults(func=command_validate)

    due = subparsers.add_parser("due", help="list due scheduled rows")
    due.add_argument("--platform", choices=["wechat_mp", "douyin"], default=None)
    due.add_argument("--now", help="ISO time, for example 2026-09-10T06:08:00+08:00")
    due.add_argument("--limit", type=int, default=20)
    due.set_defaults(func=command_due)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
