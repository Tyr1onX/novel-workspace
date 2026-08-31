#!/usr/bin/env python3
"""Read-only Fanqie analytics collector with sanitized snapshot output.

Only numeric/book-level analytics are persisted. Cookies, tokens, account identity,
bank/payment details, comments/messages, and chapter bodies are never written.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import fanqie_probe

BASE = "https://fanqienovel.com"
BOOK_MANAGE = BASE + "/main/writer/book-manage"
STATS_COMMON_PATH = "/api/author/stats/book_common_v1/v0/"
CN_TZ = timezone(timedelta(hours=8))


class ProbeError(RuntimeError):
    pass


def load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_analytics", script)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load runtime: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_book_id(novel_dir: Path) -> str:
    config = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    value = str(config.get("book_id") or "").strip()
    if not value:
        raise ProbeError(f"missing book_id: {novel_dir}")
    return value


def unwrap(body):
    return body.get("data") if isinstance(body, dict) and "data" in body else body


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


def pick(data: dict, keys: tuple[str, ...]):
    return {key: data.get(key) for key in keys if key in data}


STAT_KEYS = (
    "stats_col_time",
    "update_time",
    "reader_uv_daily",
    "reader_uv_daily_incr",
    "reader_uv_14day_cnt",
    "reader_uv_14day_incr",
    "shelf_cnt_daily",
    "shelf_cnt_daily_incr",
    "pursue_cnt_daily",
    "pursue_cnt_daily_incr",
    "reminder_cnt_daily",
    "reminder_cnt_daily_incr",
    "comment_cnt",
    "comment_cnt_incr",
    "pursue_read_rate",
    "read_completion_rate",
    "read_completion_level",
    "mark_score",
    "mark_score_incr",
)


async def click_exact(page, text: str) -> bool:
    locator = page.get_by_text(text, exact=True)
    for i in range(min(await locator.count(), 30)):
        element = locator.nth(i)
        try:
            if await element.is_visible():
                await element.click(timeout=5000)
                await page.wait_for_timeout(1200)
                return True
        except Exception:
            continue
    return False


async def capture_stats_query_template(page, runtime):
    """Capture the dashboard's own signed GET query; never persist or print it."""
    captured: dict[str, str] = {}

    def on_response(response):
        if captured:
            return
        try:
            parsed = urlparse(response.url)
            if response.request.method.upper() == "GET" and parsed.path == STATS_COMMON_PATH:
                captured.update(dict(parse_qsl(parsed.query, keep_blank_values=True)))
        except Exception:
            return

    page.on("response", on_response)
    try:
        if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
            return {}
        await page.wait_for_timeout(700)
        if not await click_exact(page, "小说数据"):
            return {}
        await page.wait_for_timeout(2200)
        return dict(captured)
    finally:
        page.remove_listener("response", on_response)


async def read_stats(page, book_id: str, query_template: dict[str, str]):
    if query_template:
        query = dict(query_template)
        query["book_id"] = book_id
        result = await get_json(page, STATS_COMMON_PATH, query)
        data = unwrap(result.get("body"))
        if isinstance(data, dict) and any(key in data for key in STAT_KEYS):
            return pick(data, STAT_KEYS)

    # Fail-soft fallback for deployments where the signed query is not required.
    for stats_type in (1, 2, 3, 4, 5, 0):
        result = await get_json(page, STATS_COMMON_PATH, {"book_id": book_id, "stats_type": stats_type})
        data = unwrap(result.get("body"))
        if isinstance(data, dict) and any(key in data for key in STAT_KEYS):
            return pick(data, STAT_KEYS)
    return {}


def first_number_after(lines: list[str], label: str):
    for i, line in enumerate(lines):
        if line != label:
            continue
        for candidate in lines[i + 1 : i + 5]:
            raw = candidate.replace(",", "").strip()
            if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
                return float(raw)
    return None


def income_from_lines(lines: list[str], expected_book_name: str):
    full_text = "\n".join(lines)
    verified = bool(expected_book_name and expected_book_name in full_text)
    cutoff = None
    for line in lines:
        match = re.search(r"统计周期截止至[:：]\s*([^每]+)", line)
        if match:
            cutoff = match.group(1).strip()
            break
    return {
        "verified_book": verified,
        "stats_through": cutoff,
        "yesterday_fanqie_income": first_number_after(lines, "昨日番茄收益") if verified else None,
        "cumulative_fanqie_income": first_number_after(lines, "累计番茄收益") if verified else None,
    }


async def read_income(page, runtime, book_name: str):
    empty = {"verified_book": False, "stats_through": None, "yesterday_fanqie_income": None, "cumulative_fanqie_income": None}
    if not book_name or not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
        return empty
    await page.wait_for_timeout(700)
    if not await click_exact(page, "小说收益"):
        return empty
    if not await click_exact(page, "切换作品"):
        return empty
    if not await click_exact(page, book_name):
        return empty
    for label in ("确定", "确认"):
        if await click_exact(page, label):
            break
    # Do not reload here. Fanqie's selected income work is page state; a reload can
    # revert to the default work and make a second book appear unverified.
    await page.wait_for_timeout(3500)
    lines = [line.strip() for line in (await page.locator("body").inner_text()).splitlines() if line.strip() and len(line.strip()) <= 160]
    return income_from_lines(lines, book_name)


def write_snapshots(novel_dirs: list[Path], report: dict, collected_at: datetime):
    filename = collected_at.strftime("%Y-%m-%dT%H-%M-%S%z") + ".json"
    written = []
    for novel_dir in novel_dirs:
        slug = novel_dir.name
        book = report["books"].get(slug)
        if not book:
            continue
        snapshot = {
            "schema_version": 1,
            "source": "fanqie-author-dashboard",
            "collected_at": collected_at.isoformat(),
            "project": slug,
            "stats": book.get("stats", {}),
            "income": book.get("income", {}),
        }
        out_dir = novel_dir / "platform-sync" / "analytics" / "snapshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(out_path))
    return written


async def run(novel_dirs: list[Path], runtime_arg: str | None, write: bool):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    projects = [(path, read_book_id(path)) for path in novel_dirs]
    collected_at = datetime.now(CN_TZ).replace(microsecond=0)

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                raise ProbeError("cannot open authenticated writer dashboard")
            await runtime.settle_page(page)

            book_list = await get_json(page, "/api/author/book/book_list/v0", {"page_index": 0, "page_count": 50})
            book_data = unwrap(book_list.get("body"))
            rows = book_data.get("book_list", []) if isinstance(book_data, dict) else []
            names = {str(row.get("book_id")): str(row.get("book_name") or "") for row in rows if isinstance(row, dict)}
            stats_template = await capture_stats_query_template(page, runtime)

            report = {"schema_version": 1, "collected_at": collected_at.isoformat(), "books": {}}
            for novel_dir, book_id in projects:
                slug = novel_dir.name
                stats = await read_stats(page, book_id, stats_template)
                income = await read_income(page, runtime, names.get(book_id, ""))
                report["books"][slug] = {"stats": stats, "income": income}

            await runtime.save_auth(context)
            if write:
                report["written_files"] = write_snapshots(novel_dirs, report, collected_at)
            print("FANQIE_DATA_PROBE_JSON_BEGIN")
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), default=str))
            print("FANQIE_DATA_PROBE_JSON_END")
            return 0
        finally:
            await runtime.close_browser_safely(browser)


def main():
    parser = argparse.ArgumentParser(description="Read and optionally persist sanitized Fanqie analytics")
    parser.add_argument("novel_dirs", nargs="+", type=Path)
    parser.add_argument("--runtime")
    parser.add_argument("--write-snapshots", action="store_true")
    args = parser.parse_args()
    try:
        return asyncio.run(run([path.resolve() for path in args.novel_dirs], args.runtime, args.write_snapshots))
    except (fanqie_probe.ProbeError, ProbeError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
