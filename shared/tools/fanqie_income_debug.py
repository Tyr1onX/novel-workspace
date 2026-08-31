#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import fanqie_probe

BASE = "https://fanqienovel.com"
BOOK_MANAGE = BASE + "/main/writer/book-manage"
INCOME_PREFIX = "/api/author/income/"


def load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_income_debug", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_book_id(novel_dir: Path) -> str:
    config = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    return str(config.get("book_id") or "").strip()


async def click_exact(page, text: str) -> bool:
    locator = page.get_by_text(text, exact=True)
    for i in range(min(await locator.count(), 30)):
        element = locator.nth(i)
        try:
            if await element.is_visible():
                await element.click(timeout=5000)
                await page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


async def get_json(page, path: str, query: dict):
    return await page.evaluate(
        """async ({path,query}) => {
          const u = new URL(path, location.origin);
          for (const [k,v] of Object.entries(query || {})) u.searchParams.set(k, String(v));
          const r = await fetch(u.toString(), {method:'GET', credentials:'include'});
          const text = await r.text();
          let body = null; try { body = JSON.parse(text); } catch (_) {}
          return {status:r.status, body};
        }""",
        {"path": path, "query": query},
    )


def unwrap(body):
    return body.get("data") if isinstance(body, dict) and "data" in body else body


SAFE_KEY = re.compile(r"(book|income|amount|total|date|time|read|listen|interaction|yesterday|summary|period)", re.I)


def sanitize(value, depth: int = 0):
    if depth > 5:
        return None
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if SAFE_KEY.search(str(key)):
                if isinstance(item, (dict, list)):
                    nested = sanitize(item, depth + 1)
                    if nested not in (None, {}, []):
                        out[str(key)] = nested
                elif isinstance(item, (str, int, float, bool)) or item is None:
                    out[str(key)] = item
            elif isinstance(item, (dict, list)):
                nested = sanitize(item, depth + 1)
                if nested not in (None, {}, []):
                    out[str(key)] = nested
        return out
    if isinstance(value, list):
        return [x for x in (sanitize(item, depth + 1) for item in value[:20]) if x not in (None, {}, [])]
    return value if isinstance(value, (str, int, float, bool)) or value is None else None


async def run(project_dirs: list[Path], runtime_arg: str | None) -> int:
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    projects = [(path.name, read_book_id(path)) for path in project_dirs]

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            templates: dict[str, dict[str, str]] = {}

            def on_response(response):
                try:
                    parsed = urlparse(response.url)
                    if response.request.method.upper() == "GET" and parsed.path.startswith(INCOME_PREFIX):
                        templates[parsed.path] = dict(parse_qsl(parsed.query, keep_blank_values=True))
                except Exception:
                    return

            page.on("response", on_response)
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                raise RuntimeError("cannot open writer dashboard")
            await page.wait_for_timeout(700)
            if not await click_exact(page, "小说收益"):
                raise RuntimeError("cannot open income dashboard")
            await page.wait_for_timeout(3500)
            page.remove_listener("response", on_response)

            report = {"templates": {}, "books": {}}
            for path, query in templates.items():
                report["templates"][path] = {"query_keys": sorted(query.keys())}

            for slug, book_id in projects:
                book_out = {}
                for path, template in templates.items():
                    query = dict(template)
                    replaced = False
                    for key in list(query):
                        if key.lower() in {"book_id", "bookid"}:
                            query[key] = book_id
                            replaced = True
                    if not replaced:
                        query["book_id"] = book_id
                    result = await get_json(page, path, query)
                    book_out[path] = {
                        "status": result.get("status"),
                        "data": sanitize(unwrap(result.get("body"))),
                    }
                report["books"][slug] = book_out

            print("FANQIE_INCOME_DEBUG_JSON_BEGIN")
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), default=str))
            print("FANQIE_INCOME_DEBUG_JSON_END")
            return 0
        finally:
            await runtime.close_browser_safely(browser)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dirs", nargs="+", type=Path)
    parser.add_argument("--runtime")
    args = parser.parse_args()
    return asyncio.run(run([p.resolve() for p in args.project_dirs], args.runtime))


if __name__ == "__main__":
    raise SystemExit(main())
