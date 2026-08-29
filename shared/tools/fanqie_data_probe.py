#!/usr/bin/env python3
"""Read-only Fanqie author analytics probe.

GET-only API reads plus navigation inspection. No chapter/content/comment mutation,
and no comment/message bodies are collected.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

import fanqie_probe


class DataProbeError(RuntimeError):
    pass


def load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_data_probe", script)
    if spec is None or spec.loader is None:
        raise DataProbeError(f"cannot load runtime: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_book_id(novel_dir: Path) -> str:
    path = novel_dir / "platform-sync" / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    book_id = str(data.get("book_id") or "").strip()
    if not book_id:
        raise DataProbeError(f"missing book_id in {path}")
    return book_id


def num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        s = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?", s):
            pct = s.endswith("%")
            try:
                v = float(s[:-1] if pct else s)
                return v / 100 if pct else v
            except ValueError:
                pass
    return None


async def get_json(page, path: str, query: dict | None = None):
    return await page.evaluate(
        """async ({path, query}) => {
          const url = new URL(path, location.origin);
          for (const [k,v] of Object.entries(query || {})) url.searchParams.set(k, String(v));
          const r = await fetch(url.toString(), {method:'GET', credentials:'include'});
          const text = await r.text();
          let body = null; try { body = JSON.parse(text); } catch (_) {}
          return {status:r.status, body};
        }""",
        {"path": path, "query": query or {}},
    )


def unwrap(result):
    body = result.get("body")
    return body.get("data") if isinstance(body, dict) and "data" in body else body


def rate_summary(rows: list[dict], key: str):
    values = [num(row.get(key)) for row in rows]
    valid = [v for v in values if v is not None]
    return {
        "available": len(valid),
        "total": len(rows),
        "avg": round(sum(valid) / len(valid), 6) if valid else None,
        "min": min(valid) if valid else None,
        "max": max(valid) if valid else None,
    }


def chapter_report(result: dict):
    data = unwrap(result)
    if not isinstance(data, dict):
        return {"http_status": result.get("status"), "available": False}
    rows = data.get("chapter_stats_list") if isinstance(data.get("chapter_stats_list"), list) else []
    selected = []
    for row in rows[-18:]:
        if not isinstance(row, dict):
            continue
        selected.append({
            "indice": row.get("indice"),
            "title": row.get("title"),
            "word_number": row.get("word_number"),
            "follow_read_rate": row.get("follow_read_rate"),
            "read_completion_rate": row.get("read_completion_rate"),
            "publish_time": row.get("publish_time"),
        })
    return {
        "http_status": result.get("status"),
        "available": True,
        "total_count": data.get("total_count"),
        "stats_update_time": data.get("stats_update_time"),
        "follow_read_rate": rate_summary(rows, "follow_read_rate"),
        "read_completion_rate": rate_summary(rows, "read_completion_rate"),
        "latest_rows": selected,
        "diag_title": data.get("diag_title"),
        "diag_detail": data.get("diag_detail"),
    }


def book_report(result: dict, book_id: str):
    data = unwrap(result)
    books = data.get("book_list") if isinstance(data, dict) else []
    if not isinstance(books, list):
        books = []
    hit = next((b for b in books if isinstance(b, dict) and str(b.get("book_id")) == book_id), None)
    if not hit:
        return {"found": False}
    keys = (
        "book_name", "word_count", "content_word_number", "chapter_number",
        "read_count", "total_impression_count", "add_bookshelf_count",
        "contract_status", "creation_status", "can_recommend", "weak_ending",
    )
    return {"found": True, **{key: hit.get(key) for key in keys}}


async def nav_candidates(page):
    return await page.locator("a,button,[role=button],[role=menuitem],[role=tab],li").evaluate_all(
        """els => els.map(e => ({tag:e.tagName, text:(e.innerText||'').trim(), href:e.href||'', role:e.getAttribute('role')||''}))
          .filter(x => x.text && x.text.length < 120 && /数据|收益|分析|收入|稿费|阅读|追读|催更|质量/.test(x.text))"""
    )


async def explore_nav(page):
    candidates = await nav_candidates(page)
    clean = []
    seen = set()
    for item in candidates:
        key = (item.get("tag"), item.get("text"), item.get("href"), item.get("role"))
        if key in seen:
            continue
        seen.add(key)
        clean.append(item)
        if len(clean) >= 60:
            break

    visits = []
    for term in ("数据分析", "收益", "收入", "稿费"):
        await page.goto("https://fanqienovel.com/writer/zone/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1200)
        locator = page.locator("a,button,[role=button],[role=menuitem],[role=tab],li").filter(has_text=term)
        count = await locator.count()
        chosen = None
        for i in range(min(count, 12)):
            el = locator.nth(i)
            text = (await el.inner_text()).strip()
            if text == term or (len(text) < 30 and term in text):
                chosen = el
                break
        if chosen is None:
            continue
        before = page.url
        try:
            await chosen.click(timeout=5000)
            await page.wait_for_timeout(1800)
        except Exception:
            continue
        body = await page.locator("body").inner_text()
        lines = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or len(line) > 180:
                continue
            if any(k in line for k in ("阅读", "追读", "催更", "收益", "收入", "稿费", "完读", "读完", "质量")):
                if line not in lines:
                    lines.append(line)
            if len(lines) >= 35:
                break
        visits.append({"term": term, "before": urlparse(before).path, "after": urlparse(page.url).path, "keyword_lines": lines})
    return {"candidates": clean, "visits": visits}


async def run(novel_dirs: list[Path], runtime_arg: str | None):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    configs = [(p.name, load_book_id(p)) for p in novel_dirs]

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            if not await runtime.goto_with_login_retry(page, "https://fanqienovel.com/writer/zone/"):
                raise DataProbeError("saved session cannot open writer zone")
            await runtime.settle_page(page)
            book_list = await get_json(page, "/api/author/book/book_list/v0", {"page_index": 0, "page_count": 50})
            report = {"books": {}}
            for slug, book_id in configs:
                chapter_stats = await get_json(page, "/api/author/stats/chapter_list_v1/v0/", {"book_id": book_id, "page_index": 0, "page_count": 200})
                report["books"][slug] = {
                    "book_id": book_id,
                    "overview": book_report(book_list, book_id),
                    "chapter_stats": chapter_report(chapter_stats),
                }
            report["navigation"] = await explore_nav(page)
            await runtime.save_auth(context)
            print("FANQIE_DATA_PROBE_JSON_BEGIN")
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
            print("FANQIE_DATA_PROBE_JSON_END")
            return 0
        finally:
            await runtime.close_browser_safely(browser)


def main():
    parser = argparse.ArgumentParser(description="Read-only Fanqie analytics probe")
    parser.add_argument("novel_dirs", nargs="+", type=Path)
    parser.add_argument("--runtime")
    args = parser.parse_args()
    try:
        return asyncio.run(run([p.resolve() for p in args.novel_dirs], args.runtime))
    except (fanqie_probe.ProbeError, DataProbeError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
