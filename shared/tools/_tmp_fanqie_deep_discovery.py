#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import fanqie_probe

BASE = "https://fanqienovel.com"
DATA_URL = BASE + "/main/writer/data?bookId={book_id}"
CHAPTER_PATH = "/api/author/stats/chapter_list_v1/v0/"
TRAFFIC_PATH = "/api/author/stats/book_increase_v2/v0/"


def load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_deep_discovery", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_book_id(novel_dir: Path) -> str:
    cfg = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    return str(cfg["book_id"])


def unwrap(body):
    return body.get("data") if isinstance(body, dict) and "data" in body else body


def safe_query(url: str, allowed: set[str]) -> dict[str, str]:
    parsed = urlparse(url)
    pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return {k: pairs[k] for k in sorted(allowed) if k in pairs}


def sanitize_chapters(body) -> dict:
    data = unwrap(body)
    if not isinstance(data, dict):
        return {}
    rows = data.get("chapter_stats_list")
    if not isinstance(rows, list):
        rows = []
    clean = []
    for row in rows[:15]:
        if not isinstance(row, dict):
            continue
        clean.append({
            "indice": row.get("indice"),
            "title": row.get("title"),
            "word_number": row.get("word_number"),
            "read_completion_rate": row.get("read_completion_rate"),
            "follow_read_rate": row.get("follow_read_rate"),
            "publish_time": row.get("publish_time"),
        })
    return {
        "total_count": data.get("total_count"),
        "stats_update_time": data.get("stats_update_time"),
        "rows_first_15": clean,
    }


def sanitize_traffic(body) -> dict:
    data = unwrap(body)
    if not isinstance(data, dict):
        return {}
    raw = data.get("data_list")
    clean = []
    if isinstance(raw, list):
        for series in raw:
            if isinstance(series, list):
                clean.append(series)
            else:
                clean.append([])
    return {"data_list": clean}


async def click_exact(page, text: str) -> bool:
    locator = page.get_by_text(text, exact=True)
    for i in range(min(await locator.count(), 30)):
        el = locator.nth(i)
        try:
            if await el.is_visible():
                await el.click(timeout=3000)
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            pass
    return False


async def discover_book(page, runtime, slug: str, book_id: str):
    captures: list[dict] = []
    tasks: set[asyncio.Task] = set()

    async def handle(response):
        try:
            u = urlparse(response.url)
            if u.netloc != "fanqienovel.com" or u.path not in {CHAPTER_PATH, TRAFFIC_PATH}:
                return
            body = await asyncio.wait_for(response.json(), timeout=4)
            if u.path == CHAPTER_PATH:
                captures.append({
                    "kind": "chapter",
                    "query": safe_query(response.url, {"latest_count", "page_count", "page_index", "stats_type"}),
                    "data": sanitize_chapters(body),
                })
            else:
                captures.append({
                    "kind": "traffic",
                    "query": safe_query(response.url, {"start_date", "end_date", "stats_types"}),
                    "data": sanitize_traffic(body),
                })
        except Exception:
            return

    def listener(response):
        task = asyncio.create_task(handle(response))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    page.on("response", listener)
    clicks: dict[str, bool] = {}
    try:
        if not await runtime.goto_with_login_retry(page, DATA_URL.format(book_id=book_id)):
            raise RuntimeError(f"cannot open data page for {slug}")
        await page.wait_for_timeout(1800)
        for label in ("质量分析", "章节完读率", "章节跟读率", "字数读完率", "流量构成", "7天", "14天", "30天"):
            clicks[label] = await click_exact(page, label)
        await page.wait_for_timeout(1800)
        if tasks:
            _, pending = await asyncio.wait(list(tasks), timeout=6)
            for task in pending:
                task.cancel()
        # Deduplicate identical requests while preserving distinct stats_type/date windows.
        unique = []
        keys = set()
        for item in captures:
            key = json.dumps({"kind": item["kind"], "query": item["query"]}, sort_keys=True, ensure_ascii=False)
            if key in keys:
                continue
            keys.add(key)
            unique.append(item)
        return {"project": slug, "clicks": clicks, "captures": unique}
    finally:
        page.remove_listener("response", listener)
        for task in list(tasks):
            task.cancel()


async def run(novel_dirs: list[Path], runtime_arg: str | None):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            reports = []
            for novel_dir in novel_dirs:
                reports.append(await discover_book(page, runtime, novel_dir.name, read_book_id(novel_dir)))
            await runtime.save_auth(context)
            print("FANQIE_DEEP_VALUES_JSON_BEGIN")
            print(json.dumps({"books": reports}, ensure_ascii=False, indent=2))
            print("FANQIE_DEEP_VALUES_JSON_END")
            return 0
        finally:
            await runtime.close_browser_safely(browser)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("novel_dirs", nargs="+", type=Path)
    ap.add_argument("--runtime")
    args = ap.parse_args()
    return asyncio.run(run([p.resolve() for p in args.novel_dirs], args.runtime))


if __name__ == "__main__":
    raise SystemExit(main())
