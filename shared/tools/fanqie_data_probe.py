#!/usr/bin/env python3
"""Read-only per-book Fanqie analytics probe.

Only author-dashboard navigation and authenticated GET requests are used. Comment,
message and chapter bodies are never collected or persisted.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import fanqie_probe

BASE = "https://fanqienovel.com"
BOOK_MANAGE = BASE + "/main/writer/book-manage"
INTERESTING = (
    "/api/author/stats/book_common_v1/v0/",
    "/api/author/stats/book_increase_v2/v0/",
    "/api/author/income/book_summary_v3/v0/",
    "/api/author/income/book_daily_v3/v0/",
)


class ProbeError(RuntimeError):
    pass


def runtime_module(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_runtime_data_probe", script)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load runtime: {script}")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def read_book_id(novel_dir: Path) -> str:
    cfg = json.loads((novel_dir / "platform-sync" / "config.json").read_text(encoding="utf-8"))
    value = str(cfg.get("book_id") or "").strip()
    if not value: raise ProbeError(f"missing book_id: {novel_dir}")
    return value


def number(v):
    if isinstance(v, bool): return None
    if isinstance(v, (int, float)) and math.isfinite(float(v)): return v
    if isinstance(v, str):
        s = v.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?", s):
            try:
                n = float(s[:-1] if s.endswith("%") else s); return n / 100 if s.endswith("%") else n
            except ValueError: pass
    return None


METRIC = ("read","reader","follow","pursue","finish","complete","retain","click","show","impression","exposure","shelf","collect","urge","remind","income","revenue","earning","amount","fee","royalty","reward","gift","comment","digg","like","recommend","rate","ratio","count","num","score","quality","pay")
BLOCK = ("content","reply","message","nickname","username","phone","email","address","intro","summary")


def numeric_metrics(value, prefix="", out=None, limit=350):
    out = {} if out is None else out
    if len(out) >= limit: return out
    if isinstance(value, dict):
        for k, child in value.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if any(x in p.lower() for x in BLOCK): continue
            numeric_metrics(child, p, out, limit)
    elif isinstance(value, list):
        for i, child in enumerate(value[:15]): numeric_metrics(child, f"{prefix}[{i}]", out, limit)
    elif any(x in prefix.lower() for x in METRIC):
        n = number(value)
        if n is not None: out[prefix] = n
    return out


def unwrap(body): return body.get("data") if isinstance(body, dict) and "data" in body else body


def value_shape(value):
    if isinstance(value, dict): return {"type":"object","keys":sorted(map(str,value.keys()))[:180]}
    if isinstance(value, list):
        first = value[0] if value else None
        return {"type":"array","length":len(value),"item_keys":sorted(map(str,first.keys()))[:180] if isinstance(first,dict) else []}
    return {"type":type(value).__name__}


def summary(result):
    body = result.get("body"); data = unwrap(body)
    out = {"http_status":result.get("status"),"shape":value_shape(data),"metrics":numeric_metrics(data)}
    if isinstance(data, dict):
        for key in ("diag_title","diag_detail","stats_col_time","update_time","stats_update_time"):
            value = data.get(key)
            if isinstance(value, (str,int,float)) and str(value).strip(): out[key] = str(value)[:800]
    if isinstance(body, dict):
        for key in ("code","message"):
            value = body.get(key)
            if isinstance(value, (str,int,float)) and str(value).strip(): out[f"response_{key}"] = str(value)[:300]
    return out


async def get_json(page, path, query):
    return await page.evaluate("""async ({path,query})=>{const u=new URL(path,location.origin);for(const[k,v]of Object.entries(query||{}))u.searchParams.set(k,String(v));const r=await fetch(u.toString(),{method:'GET',credentials:'include'});const t=await r.text();let b=null;try{b=JSON.parse(t)}catch(_){};return{status:r.status,body:b};}""", {"path":path,"query":query})


async def click_exact(page, label):
    loc = page.get_by_text(label, exact=True)
    for i in range(min(await loc.count(), 20)):
        el = loc.nth(i)
        try:
            if await el.is_visible(): await el.click(timeout=5000); await page.wait_for_timeout(3200); return True
        except Exception: continue
    return False


async def run(novel_dirs, runtime_arg):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg); runtime = runtime_module(runtime_dir); runtime.load_config()
    books = [(p.name, read_book_id(p)) for p in novel_dirs]
    captured_queries, tasks = {}, set()

    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=True); page = await context.new_page()

        async def capture(response):
            try:
                req = response.request; parsed = urlparse(response.url)
                if req.method.upper() != "GET" or parsed.netloc != "fanqienovel.com" or parsed.path not in INTERESTING: return
                query = dict(parse_qsl(parsed.query, keep_blank_values=True))
                captured_queries.setdefault(parsed.path, query)
            except Exception: return
        def on_response(response):
            t=asyncio.create_task(capture(response));tasks.add(t);t.add_done_callback(tasks.discard)
        page.on("response", on_response)

        try:
            if not await runtime.goto_with_login_retry(page, BOOK_MANAGE): raise ProbeError("cannot open authenticated writer dashboard")
            await runtime.settle_page(page)
            pages=[]
            for label in ("小说数据","小说收益"):
                await runtime.goto_with_login_retry(page, BOOK_MANAGE); await page.wait_for_timeout(900)
                ok=await click_exact(page,label); pages.append({"label":label,"clicked":ok,"path":urlparse(page.url).path})
            if tasks: await asyncio.gather(*list(tasks), return_exceptions=True)

            # Reuse exactly the dashboard's own GET query shape, substituting only book_id.
            per_book={}
            for slug,bid in books:
                per_book[slug]={"book_id":bid,"endpoints":{}}
                for path in INTERESTING:
                    q=dict(captured_queries.get(path) or {})
                    for key in list(q):
                        if "book" in key.lower() and "id" in key.lower(): q[key]=bid
                    if not q and path.startswith("/api/author/stats/"): q={"book_id":bid}
                    elif not any("book" in k.lower() and "id" in k.lower() for k in q): q["book_id"]=bid
                    per_book[slug]["endpoints"][path]=summary(await get_json(page,path,q))

            await runtime.save_auth(context)
            report={"pages":pages,"captured_query_keys":{p:sorted(q.keys()) for p,q in captured_queries.items()},"books":per_book}
            print("FANQIE_DATA_PROBE_JSON_BEGIN");print(json.dumps(report,ensure_ascii=False,separators=(",",":"),default=str));print("FANQIE_DATA_PROBE_JSON_END")
            return 0
        finally:
            page.remove_listener("response",on_response); await runtime.close_browser_safely(browser)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("novel_dirs",nargs="+",type=Path);ap.add_argument("--runtime");args=ap.parse_args()
    try:return asyncio.run(run([p.resolve() for p in args.novel_dirs],args.runtime))
    except (fanqie_probe.ProbeError,ProbeError,RuntimeError,OSError,json.JSONDecodeError) as exc:print(f"ERROR: {exc}");return 2

if __name__=="__main__":raise SystemExit(main())
