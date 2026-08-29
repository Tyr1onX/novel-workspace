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

import fanqie_probe

BASE = "https://fanqienovel.com"
BOOK_MANAGE = BASE + "/main/writer/book-manage"
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
    if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
        return {"verified_book": False, "stats_through": None, "yesterday_fanqie_income": None, "cumulative_fanqie_income": None}
    await page.wait_for_timeout(700)
    if not await click_exact(page, "小说收益"):
        return {"verified_book": False, "stats_through": None, "yesterday_fanqie_income": None, "cumulative_fanqie_income": None}
    if not await click_exact(page, "切换作品"):
        return {"verified_book": False, "stats_through": None, "yesterday_fanqie_income": None, "cumulative_fanqie_income": None}
    if not await click_exact(page, book_name):
        return {"verified_book": False, "stats_through": None, "yesterday_fanqie_income": None, "cumulative_fanqie_income": None}
    for label in ("确定", "确认"):
        if await click_exact(page, label):
            break
    await page.reload(wait_until="domcontentloaded", timeout=30000)
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

            report = {"schema_version": 1, "collected_at": collected_at.isoformat(), "books": {}}
            for novel_dir, book_id in projects:
                slug = novel_dir.name
                common = await get_json(page, "/api/author/stats/book_common_v1/v0/", {"book_id": book_id, "stats_type": 0})
                common_data = unwrap(common.get("body"))
                stats = pick(common_data, STAT_KEYS) if isinstance(common_data, dict) else {}
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
