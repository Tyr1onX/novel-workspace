#!/usr/bin/env python3
"""Read-only exploration of Fanqie author analytics.

The probe uses the saved local author session and only performs navigation and GET
reads. It never creates/edits/publishes/deletes/replies. API output is sanitized to
endpoint paths, JSON keys and numeric metrics; comment/message/content text is not
collected.
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

BASE = "https://fanqienovel.com"
BOOK_MANAGE = BASE + "/main/writer/book-manage"


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
    config = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    book_id = str(config.get("book_id") or "").strip()
    if not book_id:
        raise DataProbeError(f"missing book_id: {novel_dir}")
    return book_id


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    if isinstance(value, str):
        raw = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?", raw):
            pct = raw.endswith("%")
            try:
                val = float(raw[:-1] if pct else raw)
                return val / 100 if pct else val
            except ValueError:
                return None
    return None


METRIC_HINTS = (
    "read", "reader", "follow", "retain", "finish", "complete", "click", "show",
    "impression", "exposure", "collect", "shelf", "urge", "remind", "income",
    "revenue", "earning", "money", "amount", "royalty", "reward", "gift", "comment",
    "digg", "like", "recommend", "word", "view", "rate", "ratio", "count", "num",
    "heat", "score", "quality", "pay", "fan",
)
BLOCK_TEXT_HINTS = (
    "content", "reply", "message", "nickname", "username", "user_name", "phone",
    "mobile", "email", "address", "abstract", "summary", "intro", "title", "name",
)


def metric_leaves(value, prefix="", out=None, limit=180):
    if out is None:
        out = {}
    if len(out) >= limit:
        return out
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if any(h in path.lower() for h in BLOCK_TEXT_HINTS):
                continue
            metric_leaves(child, path, out, limit)
    elif isinstance(value, list):
        for i, child in enumerate(value[:6]):
            metric_leaves(child, f"{prefix}[{i}]", out, limit)
    else:
        if any(h in prefix.lower() for h in METRIC_HINTS):
            val = number(value)
            if val is not None:
                out[prefix] = val
    return out


def shape(value):
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(map(str, value.keys()))[:120]}
    if isinstance(value, list):
        first = value[0] if value else None
        return {
            "type": "array",
            "length": len(value),
            "item_keys": sorted(map(str, first.keys()))[:120] if isinstance(first, dict) else [],
        }
    return {"type": type(value).__name__}


def unwrap(body):
    return body.get("data") if isinstance(body, dict) and "data" in body else body


async def get_json(page, path: str, query: dict | None = None):
    return await page.evaluate(
        """async ({path, query}) => {
          const u = new URL(path, location.origin);
          for (const [k,v] of Object.entries(query || {})) u.searchParams.set(k, String(v));
          const r = await fetch(u.toString(), {method:'GET', credentials:'include'});
          const text = await r.text();
          let body = null; try { body = JSON.parse(text); } catch (_) {}
          return {status:r.status, body};
        }""",
        {"path": path, "query": query or {}},
    )


def chapter_stats(result):
    data = unwrap(result.get("body"))
    if not isinstance(data, dict):
        return {"status": result.get("status"), "available": False}
    rows = data.get("chapter_stats_list") if isinstance(data.get("chapter_stats_list"), list) else []
    usable_follow = [number(x.get("follow_read_rate")) for x in rows if isinstance(x, dict)]
    usable_finish = [number(x.get("read_completion_rate")) for x in rows if isinstance(x, dict)]
    usable_follow = [x for x in usable_follow if x is not None]
    usable_finish = [x for x in usable_finish if x is not None]
    return {
        "status": result.get("status"),
        "total_count": data.get("total_count"),
        "stats_update_time": data.get("stats_update_time"),
        "follow_read_rate_values": len(usable_follow),
        "read_completion_rate_values": len(usable_finish),
        "diag_title_present": bool(data.get("diag_title")),
        "diag_detail_present": bool(data.get("diag_detail")),
    }


async def short_candidates(page):
    return await page.locator("a,button,[role=button],[role=menuitem],[role=tab],li,span").evaluate_all(
        """els => els.map(e => ({tag:e.tagName,text:(e.innerText||'').trim(),href:e.href||'',role:e.getAttribute('role')||''}))
        .filter(x => x.text && x.text.length <= 80 && /数据|收益|收入|稿费|分析|阅读|追读|催更|质量|作品/.test(x.text))"""
    )


def sanitize_candidates(items):
    out, seen = [], set()
    for item in items:
        key = (item.get("text"), item.get("href"), item.get("tag"), item.get("role"))
        if key in seen:
            continue
        seen.add(key)
        href = item.get("href") or ""
        out.append({
            "text": item.get("text"),
            "path": urlparse(href).path if href.startswith(BASE) else "",
            "tag": item.get("tag"),
            "role": item.get("role"),
        })
        if len(out) >= 100:
            break
    return out


async def keyword_lines(page):
    text = await page.locator("body").inner_text()
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) > 160:
            continue
        if any(k in line for k in ("阅读", "追读", "催更", "收益", "收入", "稿费", "完读", "读完", "质量", "展现", "点击", "书架")):
            if line not in out:
                out.append(line)
        if len(out) >= 60:
            break
    return out


async def run(novel_dirs: list[Path], runtime_arg: str | None):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()
    books = [(p.name, load_book_id(p)) for p in novel_dirs]
    captured = {}
    pending = set()

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()

        async def capture(response):
            try:
                request = response.request
                if request.method.upper() != "GET":
                    return
                parsed = urlparse(response.url)
                if parsed.netloc != "fanqienovel.com" or "/api/author/" not in parsed.path:
                    return
                record = captured.setdefault(parsed.path, {"path": parsed.path, "statuses": set(), "shape": None, "metrics": {}})
                record["statuses"].add(response.status)
                if "json" not in (response.headers.get("content-type") or "").lower():
                    return
                body = await response.json()
                data = unwrap(body)
                if record["shape"] is None:
                    record["shape"] = shape(data)
                record["metrics"].update(metric_leaves(data))
            except Exception:
                return

        def on_response(response):
            task = asyncio.create_task(capture(response))
            pending.add(task)
            task.add_done_callback(pending.discard)

        page.on("response", on_response)
        try:
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                raise DataProbeError("saved session cannot open authenticated book manager")
            await runtime.settle_page(page)
            await page.wait_for_timeout(1800)

            report = {"start_path": urlparse(page.url).path, "books": {}, "pages": []}
            for slug, book_id in books:
                result = await get_json(page, "/api/author/stats/chapter_list_v1/v0/", {
                    "book_id": book_id, "page_index": 0, "page_count": 200,
                })
                report["books"][slug] = {"book_id": book_id, "chapter_stats": chapter_stats(result)}

            report["pages"].append({
                "path": urlparse(page.url).path,
                "candidates": sanitize_candidates(await short_candidates(page)),
                "keyword_lines": await keyword_lines(page),
            })

            # Navigate only through short, clearly analytics/revenue labels. This is UI navigation,
            # not an author action. Prefer hrefs; otherwise click a single exact/short match.
            for term in ("数据分析", "数据", "作品数据", "收益", "收入", "稿费", "质量分析"):
                if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                    continue
                await page.wait_for_timeout(1000)
                elements = page.locator("a,button,[role=button],[role=menuitem],[role=tab],li,span").filter(has_text=term)
                chosen = None
                for i in range(min(await elements.count(), 25)):
                    el = elements.nth(i)
                    try:
                        text = (await el.inner_text()).strip()
                        if text == term or (term in text and len(text) <= 24):
                            chosen = el
                            break
                    except Exception:
                        continue
                if chosen is None:
                    continue
                try:
                    await chosen.click(timeout=5000)
                    await page.wait_for_timeout(2200)
                except Exception:
                    continue
                current = urlparse(page.url).path
                if current == urlparse(BOOK_MANAGE).path:
                    continue
                report["pages"].append({
                    "term": term,
                    "path": current,
                    "candidates": sanitize_candidates(await short_candidates(page)),
                    "keyword_lines": await keyword_lines(page),
                })

            if pending:
                await asyncio.gather(*list(pending), return_exceptions=True)
            await runtime.save_auth(context)
            report["author_get_apis"] = [
                {"path": row["path"], "statuses": sorted(row["statuses"]), "shape": row["shape"], "metrics": row["metrics"]}
                for row in sorted(captured.values(), key=lambda x: x["path"])
            ]
            print("FANQIE_DATA_PROBE_JSON_BEGIN")
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), default=str))
            print("FANQIE_DATA_PROBE_JSON_END")
            return 0
        finally:
            page.remove_listener("response", on_response)
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
