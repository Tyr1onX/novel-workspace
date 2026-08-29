#!/usr/bin/env python3
"""Discover repository novel projects configured for Fanqie synchronization.

The output is deliberately line-oriented so the same helper is easy to consume from
Bash and Windows PowerShell GitHub Actions steps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class ProjectError(RuntimeError):
    pass


def discover(root: Path) -> list[tuple[Path, dict]]:
    novels = root / "novels"
    projects: list[tuple[Path, dict]] = []
    for config_path in sorted(novels.glob("*/platform-sync/config.json")):
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectError(f"cannot read {config_path}: {exc}") from exc
        if config.get("platform") != "fanqie":
            continue
        novel_dir = config_path.parent.parent
        projects.append((novel_dir, config))
    return projects


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Fanqie-configured novel projects")
    parser.add_argument("command", choices=["list", "enabled", "any-enabled", "pending-one-shots"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    projects = discover(root)

    if args.command == "list":
        for novel_dir, _config in projects:
            print(rel(root, novel_dir))
        return 0

    if args.command == "enabled":
        for novel_dir, config in projects:
            if config.get("sync_enabled") is True:
                print(rel(root, novel_dir))
        return 0

    if args.command == "any-enabled":
        print("true" if any(c.get("sync_enabled") is True for _d, c in projects) else "false")
        return 0

    if args.command == "pending-one-shots":
        for novel_dir, _config in projects:
            request_path = novel_dir / "platform-sync" / "one-shot.json"
            if not request_path.is_file():
                continue
            try:
                request = json.loads(request_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProjectError(f"cannot read {request_path}: {exc}") from exc
            if (
                request.get("status", "pending") == "pending"
                and request.get("authorized") is True
                and (request.get("audit") or {}).get("status") == "passed"
            ):
                print(f"{rel(root, novel_dir)}|{rel(root, request_path)}")
        return 0

    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
