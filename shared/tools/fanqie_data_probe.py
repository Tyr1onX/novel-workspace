#!/usr/bin/env python3
"""Read-only Fanqie long-form author analytics discovery.

Uses the saved local author session. Only GET responses are inspected. Output is
sanitized to endpoint paths, response keys, numeric metrics and short analytics UI
labels. Comment/message/content bodies are never collected.
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


class ProbeError(RuntimeError):
    pass


def runtime_module(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_data_probe", script)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load runtime: {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def book_id(novel_dir: Path) -> str:
    data = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    value = str(data.get("book_id") or "").strip()
    if not value:
        raise ProbeError(f"missing book_id: {novel_dir}")
    return value


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    if isinstance(value, str):
        raw = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?", raw):
            try:
                value = float(raw[:-1] if raw.endswith("%") else raw)
                return value / 100 if raw.endswith("%") else value
            except ValueError:
                pass
    return None


METRIC = (
    "read", "reader", "follow", "finish", "complete", "retain", "click", "show",
    "impression", "exposure", "shelf", "collect", "urge", "remind", "income",
    "revenue", "earning", "amount", "royalty", "reward", "gift", "comment", "digg",
    "like", "recommend", "rate", "ratio", "count", "num", "score", "quality", "pay",
)
BLOCK = ("content", "reply", "message", "nickname", "username", "phone", "email", "address", "title", "name", "intro", "summary")


def metrics(value, prefix="", out=None, limit=240):
    out = {} if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if any(x in path.lower() for x in BLOCK):
                continue
            metrics(child, path, out, limit)
    elif isinstance(value, list):
        for i, child in enumerate(value[:8]):
            metrics(child, f"{prefix}[{i}]", out, limit)
    elif any(x in prefix.lower() for x in METRIC):
        n = number(value)
        if n is not None:
            out[prefix] = n
    return out


def unwrap(body):
    return body.get("data") if isinstance(body, dict) and "data" in body else body


def shape(value):
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(map(str, value.keys()))[:160]}
    if isinstance(value, list):
        first = value[0] if value else None
        return {"type": "array", "length": len(value), "item_keys": sorted(map(str, first.keys()))[:160] if isinstance(first, dict) else []}
    return {"type": type(value).__name__}


async def get_json(page, path, query):
    return await page.evaluate(
        """async ({path,query}) => {
          const u=new URL(path,location.origin); for(const [k,v] of Object.entries(query||{}))u.searchParams.set(k,String(v));
          const r=await fetch(u.toString(),{method:'GET',credentials:'include'}); const t=await r.text(); let b=null; try{b=JSON.parse(t)}catch(_){};
          return {status:r.status,body:b};
        }""",
        {"path": path, "query": query},
    )


async def analytic_lines(page):
    body = await page.locator("body").inner_text()
    words = ("阅读", "追读", "催更", "收益", "收入", "稿费", "完读", "读完", "展现", "点击", "书架", "质量", "推荐")
    out = []
    for raw in body.splitlines():
        line = raw.strip()
        if line and len(line) <= 140 and any(w in line for w in words) and line not in out:
            out.append(line)
        if len(out) >= 80:
            break
    return out


async def click_exact(page, text):
    loc = page.get_by_text(text, exact=True)
    for i in range(min(await loc.count(), 20)):
        el = loc.nth(i)
        try:
            if await el.is_visible():
                await el.click(timeout=5000)
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            continue
    return False


async def run(novel_dirs, runtime_arg):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = runtime_module(runtime_dir)
    runtime.load_config()
    books = [(p.name, book_id(p)) for p in novel_dirs]
    captured, tasks = {}, set()

    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=True)
        page = await context.new_page()

        async def capture(response):
            try:
                req = response.request
                parsed = urlparse(response.url)
                if req.method.upper() != "GET" or parsed.netloc != "fanqienovel.com" or "/api/author/" not in parsed.path:
                    return
                row = captured.setdefault(parsed.path, {"path": parsed.path, "statuses": set(), "shape": None, "metrics": {}})
                row["statuses"].add(response.status)
                if "json" not in (response.headers.get("content-type") or "").lower():
                    return
                data = unwrap(await response.json())
                row["shape"] = row["shape"] or shape(data)
                row["metrics"].update(metrics(data))
            except Exception:
                return

        def on_response(response):
            task = asyncio.create_task(capture(response)); tasks.add(task); task.add_done_callback(tasks.discard)

        page.on("response", on_response)
        try:
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                raise ProbeError("cannot open authenticated writer dashboard")
            await runtime.settle_page(page)
            await page.wait_for_timeout(1500)

            report = {"books": {}, "pages": []}
            for slug, bid in books:
                result = await get_json(page, "/api/author/stats/chapter_list_v1/v0/", {"book_id": bid, "page_index": 0, "page_count": 200})
                data = unwrap(result.get("body"))
                rows = data.get("chapter_stats_list", []) if isinstance(data, dict) else []
                report["books"][slug] = {
                    "book_id": bid,
                    "chapter_stats_status": result.get("status"),
                    "chapter_count": data.get("total_count") if isinstance(data, dict) else None,
                    "follow_rate_populated": sum(1 for x in rows if isinstance(x, dict) and number(x.get("follow_read_rate")) is not None),
                    "completion_rate_populated": sum(1 for x in rows if isinstance(x, dict) and number(x.get("read_completion_rate")) is not None),
                }

            for label in ("小说数据", "小说收益"):
                if not await runtime.goto_with_login_retry(page, BOOK_MANAGE):
                    continue
                await page.wait_for_timeout(1000)
                ok = await click_exact(page, label)
                report["pages"].append({
                    "label": label,
                    "clicked": ok,
                    "path": urlparse(page.url).path,
                    "lines": await analytic_lines(page) if ok else [],
                })

            if tasks:
                await asyncio.gather(*list(tasks), return_exceptions=True)
            await runtime.save_auth(context)
            report["author_get_apis"] = [
                {"path": x["path"], "statuses": sorted(x["statuses"]), "shape": x["shape"], "metrics": x["metrics"]}
                for x in sorted(captured.values(), key=lambda y: y["path"])
            ]
            print("FANQIE_DATA_PROBE_JSON_BEGIN")
            print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), default=str))
            print("FANQIE_DATA_PROBE_JSON_END")
            return 0
        finally:
            page.remove_listener("response", on_response)
            await runtime.close_browser_safely(browser)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("novel_dirs", nargs="+", type=Path)
    parser.add_argument("--runtime")
    args = parser.parse_args()
    try:
        return asyncio.run(run([p.resolve() for p in args.novel_dirs], args.runtime))
    except (fanqie_probe.ProbeError, ProbeError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
