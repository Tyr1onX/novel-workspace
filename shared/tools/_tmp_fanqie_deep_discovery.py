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


def shape(value, depth: int = 0):
    if depth >= 3:
        if isinstance(value, dict):
            return {"type": "object", "keys": sorted(map(str, value.keys()))[:80]}
        if isinstance(value, list):
            return {"type": "array", "length": len(value)}
        return type(value).__name__
    if isinstance(value, dict):
        return {str(k): shape(v, depth + 1) for k, v in list(value.items())[:80]}
    if isinstance(value, list):
        return {"type": "array", "length": len(value), "sample": shape(value[0], depth + 1) if value else None}
    return type(value).__name__


async def click_exact(page, text: str) -> bool:
    locator = page.get_by_text(text, exact=True)
    for i in range(min(await locator.count(), 30)):
        el = locator.nth(i)
        try:
            if await el.is_visible():
                await el.click(timeout=3000)
                await page.wait_for_timeout(1300)
                return True
        except Exception:
            pass
    return False


async def discover_book(page, runtime, slug: str, book_id: str):
    seen: dict[str, dict] = {}
    tasks: set[asyncio.Task] = set()

    async def handle(response):
        try:
            u = urlparse(response.url)
            if u.netloc != "fanqienovel.com" or not u.path.startswith("/api/author/"):
                return
            ctype = (response.headers or {}).get("content-type", "")
            if "json" not in ctype.lower():
                return
            body = await asyncio.wait_for(response.json(), timeout=4)
            query_keys = sorted(k for k, _ in parse_qsl(u.query, keep_blank_values=True))
            key = f"{response.request.method.upper()} {u.path}?{','.join(query_keys)}"
            seen[key] = {"status": response.status, "shape": shape(body)}
        except Exception:
            return

    def listener(response):
        task = asyncio.create_task(handle(response))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    page.on("response", listener)
    try:
        if not await runtime.goto_with_login_retry(page, DATA_URL.format(book_id=book_id)):
            raise RuntimeError(f"cannot open data page for {slug}")
        await page.wait_for_timeout(1800)
        for label in ("质量分析", "章节完读率", "章节跟读率", "字数读完率", "流量构成", "7天", "14天", "30天"):
            await click_exact(page, label)
        await page.wait_for_timeout(1800)
        if tasks:
            done, pending = await asyncio.wait(list(tasks), timeout=6)
            for task in pending:
                task.cancel()
        return {"project": slug, "book_id_length": len(book_id), "endpoints": seen}
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
            print("FANQIE_DEEP_DISCOVERY_JSON_BEGIN")
            print(json.dumps({"books": reports}, ensure_ascii=False, indent=2))
            print("FANQIE_DEEP_DISCOVERY_JSON_END")
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
