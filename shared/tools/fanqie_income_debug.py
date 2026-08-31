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
                await page.wait_for_timeout(900)
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


def first_number_after(lines: list[str], label: str):
    for i, line in enumerate(lines):
        if line != label:
            continue
        for candidate in lines[i + 1 : i + 5]:
            raw = candidate.replace(",", "").strip()
            if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
                return float(raw)
    return None


def page_income(lines: list[str]):
    cutoff = None
    for line in lines:
        match = re.search(r"统计周期截止至[:：]\s*([^每]+)", line)
        if match:
            cutoff = match.group(1).strip()
            break
    return {
        "stats_through": cutoff,
        "yesterday_fanqie_income": first_number_after(lines, "昨日番茄收益"),
        "cumulative_fanqie_income": first_number_after(lines, "累计番茄收益"),
    }


async def run(project_dirs: list[Path], runtime_arg: str | None) -> int:
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    projects = [(path.name, read_book_id(path)) for path in project_dirs]

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                raise RuntimeError("cannot open writer dashboard")
            await page.wait_for_timeout(700)

            book_list = await get_json(page, "/api/author/book/book_list/v0", {"page_index": 0, "page_count": 50})
            book_data = unwrap(book_list.get("body"))
            rows = book_data.get("book_list", []) if isinstance(book_data, dict) else []
            names = {str(row.get("book_id")): str(row.get("book_name") or "") for row in rows if isinstance(row, dict)}

            if not await click_exact(page, "小说收益"):
                raise RuntimeError("cannot open income dashboard")
            await page.wait_for_timeout(2500)

            report = {"books": {}}
            for slug, book_id in projects:
                book_name = names.get(book_id, "")
                captured: dict[str, dict[str, str]] = {}

                def on_response(response):
                    try:
                        parsed = urlparse(response.url)
                        if response.request.method.upper() == "GET" and parsed.path.startswith(INCOME_PREFIX):
                            captured[parsed.path] = dict(parse_qsl(parsed.query, keep_blank_values=True))
                    except Exception:
                        return

                page.on("response", on_response)
                switched = False
                if await click_exact(page, "切换作品"):
                    if book_name and await click_exact(page, book_name):
                        switched = True
                        for label in ("确定", "确认"):
                            if await click_exact(page, label):
                                break
                await page.wait_for_timeout(2600)
                page.remove_listener("response", on_response)

                lines = [line.strip() for line in (await page.locator("body").inner_text()).splitlines() if line.strip() and len(line.strip()) <= 160]
                exact_responses = {}
                for path, query in captured.items():
                    result = await get_json(page, path, query)
                    exact_responses[path] = {
                        "status": result.get("status"),
                        "book_id_query": query.get("book_id"),
                        "data": sanitize(unwrap(result.get("body"))),
                    }

                report["books"][slug] = {
                    "expected_book_id": book_id,
                    "expected_book_name": book_name,
                    "switch_clicked": switched,
                    "body_has_book_name": bool(book_name and book_name in "\n".join(lines)),
                    "page_income": page_income(lines),
                    "responses": exact_responses,
                }

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
