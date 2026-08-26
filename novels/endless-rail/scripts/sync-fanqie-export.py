#!/usr/bin/env python3
"""Sync a Fanqie author-editor full-book export into the Endless Rail workspace.

Usage (from repo root):
    python novels/endless-rail/scripts/sync-fanqie-export.py "C:\\path\\to\\fanqie-export.md"

Defaults:
- expects every chapter to come from source=author-editor;
- treats chapters 1..59 as published and later chapters as pending/scheduled;
- writes one Markdown file per chapter;
- rewrites chapters/index.md and chapters/platform-source.json;
- refuses to overwrite uncommitted chapter edits unless --force is supplied;
- does NOT commit or push unless explicitly requested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CHAPTER_RE = re.compile(
    r"^## 第(?P<number>\d+)章 (?P<title>.+?)\n\n"
    r"<!-- item_id=(?P<item_id>\d+); status=(?P<status>.*?); "
    r"source=(?P<source>.*?); platform_words=(?P<platform_words>\d+); "
    r"exported_chars=(?P<exported_chars>\d+) -->\n\n",
    re.MULTILINE,
)
BOOK_ID_RE = re.compile(r"^> book_id:\s*(\d+)\s*$", re.MULTILINE)
EXPORT_TIME_RE = re.compile(r"^> 导出时间:\s*(.+?)\s*$", re.MULTILINE)
SUCCESS_RE = re.compile(r"^> 成功章节:\s*(\d+)\s*/\s*(\d+)\s*$", re.MULTILINE)


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_repo(explicit: Path | None) -> Path:
    if explicit:
        repo = explicit.resolve()
    else:
        here = Path.cwd().resolve()
        probe = run_git(here, "rev-parse", "--show-toplevel", check=False)
        if probe.returncode != 0:
            raise SystemExit("当前目录不在 Git 仓库中，请用 --repo 指定 novel-workspace。")
        repo = Path(probe.stdout.strip()).resolve()

    expected = repo / "novels" / "endless-rail"
    if not expected.is_dir():
        raise SystemExit(f"不是预期的 novel-workspace：缺少 {expected}")
    return repo


def parse_export(path: Path, allow_reader: bool) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    matches = list(CHAPTER_RE.finditer(raw))
    if not matches:
        raise SystemExit("没有识别到番茄导出章节。请确认使用当前全文导出脚本生成的 Markdown。")

    success = SUCCESS_RE.search(raw)
    if success and success.group(1) != success.group(2):
        raise SystemExit(f"导出并不完整：{success.group(1)}/{success.group(2)}")

    book_id_m = BOOK_ID_RE.search(raw)
    export_time_m = EXPORT_TIME_RE.search(raw)
    first_line = raw.splitlines()[0].strip() if raw.splitlines() else ""
    book_name = first_line.removeprefix("# ").strip() or "未命名作品"

    chapters = []
    for i, match in enumerate(matches):
        number = int(match.group("number"))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[match.end():end].strip()
        source = match.group("source").strip()
        if source != "author-editor" and not allow_reader:
            raise SystemExit(
                f"第{number}章来源是 {source!r}，不是 author-editor。"
                "请重新用‘作者编辑器优先’版本导出，或显式加 --allow-reader。"
            )
        if not body:
            raise SystemExit(f"第{number}章正文为空。")
        chapters.append(
            {
                "number": number,
                "title": match.group("title").strip(),
                "item_id": match.group("item_id"),
                "platform_status": match.group("status").strip(),
                "source": source,
                "platform_words": int(match.group("platform_words")),
                "exported_chars": int(match.group("exported_chars")),
                "body": body,
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            }
        )

    numbers = [c["number"] for c in chapters]
    expected = list(range(numbers[0], numbers[-1] + 1))
    if numbers != expected or numbers[0] != 1:
        raise SystemExit(f"章节编号不连续：{numbers[:5]} ... {numbers[-5:]}")

    return {
        "book_name": book_name,
        "book_id": book_id_m.group(1) if book_id_m else "",
        "export_time": export_time_m.group(1).strip() if export_time_m else "",
        "chapters": chapters,
        "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def ensure_clean(repo: Path, force: bool) -> None:
    target = "novels/endless-rail/chapters"
    proc = run_git(repo, "status", "--porcelain", "--", target, check=False)
    dirty = proc.stdout.strip()
    if dirty and not force:
        print("检测到 chapters/ 有未提交修改：", file=sys.stderr)
        print(dirty, file=sys.stderr)
        raise SystemExit("为避免覆盖未提交正文，已停止。确认这些修改可以丢弃后再加 --force。")


def clean_old_chapter_files(chapters_dir: Path) -> None:
    for volume in (chapters_dir / "volume-01", chapters_dir / "volume-02"):
        volume.mkdir(parents=True, exist_ok=True)
        for path in volume.iterdir():
            if path.is_file() and (
                re.fullmatch(r"chapter-\d{3}\.md", path.name)
                or re.fullmatch(r"chapters-\d{3}-\d{3}\.md", path.name)
            ):
                path.unlink()


def write_chapters(project: Path, data: dict) -> None:
    chapters_dir = project / "chapters"
    clean_old_chapter_files(chapters_dir)

    for chapter in data["chapters"]:
        n = chapter["number"]
        volume = "volume-01" if n <= 35 else "volume-02"
        out = chapters_dir / volume / f"chapter-{n:03d}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            f"# 第{n}章 {chapter['title']}\n\n{chapter['body'].rstrip()}\n",
            encoding="utf-8",
        )


def write_index(project: Path, data: dict, published_through: int) -> None:
    lines = [
        "# 章节索引",
        "",
        "> 本索引由 `scripts/sync-fanqie-export.py` 根据番茄作者后台全文导出生成。",
        "> 番茄后台为已发布事实源；同步完成后仓库逐章正文为后续续写事实源。",
        "",
        f"- 作品：**{data['book_name']}**",
        f"- Fanqie book_id：`{data['book_id']}`",
        f"- 导出时间：{data['export_time'] or '未知'}",
        f"- 当前同步：第1～{len(data['chapters'])}章",
        f"- 已发布边界：第{published_through}章",
        "",
        "| 章 | 标题 | 番茄字数 | 发布状态 | item_id |",
        "|---:|---|---:|---|---|",
    ]
    for c in data["chapters"]:
        state = "已发布" if c["number"] <= published_through else "待发布/定时稿"
        title = c["title"].replace("|", "\\|")
        lines.append(
            f"| {c['number']} | {title} | {c['platform_words']} | {state} | `{c['item_id']}` |"
        )

    lines += [
        "",
        "## 卷进度",
        "",
        "- 第一卷《初生移动站》：第1～35章。",
        f"- 第二卷《北境七站》：第36～{len(data['chapters'])}章，进行中。",
        "",
        "## 下一章",
        "",
        f"第{len(data['chapters']) + 1}章。续写前读取 `docs/next-window-handoff.md`、最新三章、`docs/writing-rules.md`。",
        "",
    ]
    (project / "chapters" / "index.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(project: Path, data: dict, published_through: int, source_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "book_name": data["book_name"],
        "book_id": data["book_id"],
        "export_time": data["export_time"],
        "source_file_name": source_path.name,
        "source_file_sha256": data["raw_sha256"],
        "chapter_count": len(data["chapters"]),
        "published_through": published_through,
        "synced_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "chapters": [
            {k: c[k] for k in (
                "number", "title", "item_id", "platform_words", "exported_chars", "source", "sha256"
            )}
            for c in data["chapters"]
        ],
    }
    (project / "chapters" / "platform-source.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def update_readme(project: Path, data: dict, published_through: int) -> None:
    last = data["chapters"][-1]
    next_n = last["number"] + 1
    title = data["book_name"]
    body = f"""# 《{title}》

番茄小说持续更新项目。该目录只保存本书自己的正文、设定、大纲、连续性账本和平台进度，不与其他小说共享世界观或人物资料。

## 当前状态

- 平台：番茄小说
- Fanqie book_id：`{data['book_id']}`
- 仓库正文：第1～{last['number']}章
- 已发布：第1～{published_through}章
- 待发布/定时稿：第{published_through + 1}～{last['number']}章
- 第一卷《初生移动站》：已完成（1～35章）
- 第二卷《北境七站》：进行中
- 最新稿：第{last['number']}章《{last['title']}》
- 下一章：第{next_n}章
- 当前主线：炉坪工务站阶段收束，旧港路线首次获得实体工务证据

## 续写前必读

1. `novels/endless-rail/docs/next-window-handoff.md`
2. `novels/endless-rail/chapters/volume-02/chapter-{last['number'] - 2:03d}.md`
3. `novels/endless-rail/chapters/volume-02/chapter-{last['number'] - 1:03d}.md`
4. `novels/endless-rail/chapters/volume-02/chapter-{last['number']:03d}.md`
5. `novels/endless-rail/docs/writing-rules.md`
6. `novels/endless-rail/docs/long-term-outline.md`
7. `novels/endless-rail/docs/master-outline.md`

`chapters/platform-source.json` 记录本次番茄后台同步的 item_id、字数与正文哈希，用于以后检查平台/仓库漂移。

## 目录

- `chapters/`：逐章正文、章节索引、平台同步清单
- `docs/`：世界观、总纲、短期大纲、连续性账本、写作规则和续写交接
- `scripts/`：番茄平台同步工具

## 事实源优先级

1. 已发布章节发生冲突时，以番茄实际已发布正文为事实。
2. 完成平台同步后，以仓库逐章正文作为后续续写事实源。
3. `shared/` 只提供跨小说方法和规则，不得覆盖本书已经发生的剧情。
"""
    (project / "README.md").write_text(body, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="同步番茄作者后台全文导出到 Endless Rail 仓库。")
    parser.add_argument("export", type=Path, help="番茄全文导出的 Markdown 文件")
    parser.add_argument("--repo", type=Path, help="novel-workspace 根目录；默认自动识别当前 Git 仓库")
    parser.add_argument("--published-through", type=int, default=59, help="已经真实发布到平台的最后一章，默认 59")
    parser.add_argument("--allow-reader", action="store_true", help="允许 source=reader；通常不建议")
    parser.add_argument("--force", action="store_true", help="覆盖 chapters/ 下未提交修改")
    parser.add_argument("--commit", action="store_true", help="同步完成后自动 git commit")
    parser.add_argument("--push", action="store_true", help="同步并提交后自动 git push；必须同时使用 --commit")
    args = parser.parse_args()

    export = args.export.expanduser().resolve()
    if not export.is_file():
        raise SystemExit(f"找不到导出文件：{export}")
    if args.push and not args.commit:
        raise SystemExit("--push 必须与 --commit 一起使用。")

    repo = find_repo(args.repo)
    project = repo / "novels" / "endless-rail"
    data = parse_export(export, args.allow_reader)

    if not (1 <= args.published_through <= len(data["chapters"])):
        raise SystemExit("--published-through 超出章节范围。")

    print(f"作品：{data['book_name']}")
    print(f"book_id：{data['book_id']}")
    print(f"章节：1～{len(data['chapters'])}")
    print(f"来源：{sorted(set(c['source'] for c in data['chapters']))}")
    print(f"已发布边界：{args.published_through}")

    ensure_clean(repo, args.force)
    write_chapters(project, data)
    write_index(project, data, args.published_through)
    write_manifest(project, data, args.published_through, export)
    update_readme(project, data, args.published_through)

    print("\n同步完成。")
    print("已写入：")
    print("  novels/endless-rail/chapters/volume-01/chapter-001.md ... chapter-035.md")
    print(f"  novels/endless-rail/chapters/volume-02/chapter-036.md ... chapter-{len(data['chapters']):03d}.md")
    print("  novels/endless-rail/chapters/index.md")
    print("  novels/endless-rail/chapters/platform-source.json")
    print("  novels/endless-rail/README.md")

    if args.commit:
        run_git(repo, "add", "novels/endless-rail")
        msg = f"recover endless-rail from Fanqie through chapter {len(data['chapters'])}"
        commit = run_git(repo, "commit", "-m", msg, check=False)
        if commit.returncode != 0:
            print(commit.stdout)
            print(commit.stderr, file=sys.stderr)
            raise SystemExit("git commit 失败。")
        print(commit.stdout.strip())
        if args.push:
            pushed = run_git(repo, "push", check=False)
            if pushed.returncode != 0:
                print(pushed.stdout)
                print(pushed.stderr, file=sys.stderr)
                raise SystemExit("git push 失败。")
            print(pushed.stdout.strip() or pushed.stderr.strip())
    else:
        print("\n未自动提交。请先检查 git diff；确认后再 commit/push。")


if __name__ == "__main__":
    main()
