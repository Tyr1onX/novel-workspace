#!/usr/bin/env python3
"""Read-only Fanqie author analytics probe.

Only authenticated GET requests are issued. The probe never creates, edits,
publishes, deletes, reschedules, or replies to anything. It prints numeric
analytics and response structure only; comment/message text is not collected.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

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
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataProbeError(f"cannot read {path}: {exc}") from exc
    book_id = str(config.get("book_id") or "").strip()
    if not book_id:
        raise DataProbeError(f"missing book_id in {path}")
    return book_id


def as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    if isinstance(value, str):
        text = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?", text):
            pct = text.endswith("%")
            try:
                number = float(text[:-1] if pct else text)
                return number / 100 if pct else number
            except ValueError:
                pass
    return None


METRIC_WORDS = (
    "read", "reader", "follow", "retain", "finish", "complete", "click",
    "show", "impression", "exposure", "collect", "shelf", "urge", "remind",
    "income", "revenue", "earning", "money", "amount", "gift", "comment",
    "like", "recommend", "word", "view", "rate", "ratio", "count", "num",
    "heat", "score", "quality",
)
BLOCKED_WORDS = (
    "content", "reply", "message", "nickname", "phone", "mobile", "email",
    "address", "abstract", "summary",
)


def collect_metrics(value, prefix="", output=None, limit=160):
    if output is None:
        output = {}
    if len(output) >= limit:
        return output
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lower = path.lower()
            if any(word in lower for word in BLOCKED_WORDS):
                continue
            collect_metrics(child, path, output, limit)
    elif isinstance(value, list):
        for index, child in enumerate(value[:8]):
            collect_metrics(child, f"{prefix}[{index}]", output, limit)
    else:
        lower = prefix.lower()
        if any(word in lower for word in METRIC_WORDS):
            number = as_number(value)
            if number is not None:
                output[prefix] = number
    return output


def shape(value):
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(value.keys())[:100]}
    if isinstance(value, list):
        first = value[0] if value else None
        return {
            "type": "array",
            "length": len(value),
            "item_keys": sorted(first.keys())[:100] if isinstance(first, dict) else [],
        }
    return {"type": type(value).__name__}


async def get_json(page, path: str, query: dict):
    return await page.evaluate(
        """async ({path, query}) => {
          const url = new URL(path, location.origin);
          for (const [key, value] of Object.entries(query || {})) {
            url.searchParams.set(key, String(value));
          }
          const response = await fetch(url.toString(), {method: 'GET', credentials: 'include'});
          const text = await response.text();
          let body = null;
          try { body = JSON.parse(text); } catch (_) {}
          return {status: response.status, body};
        }""",
        {"path": path, "query": query},
    )


def summarize(label: str, result: dict):
    body = result.get("body")
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    return {
        "label": label,
        "status": result.get("status"),
        "shape": shape(data),
        "metrics": collect_metrics(data),
    }


async def run(novel_dirs: list[Path], runtime_arg: str | None):
    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = load_runtime(runtime_dir)
    runtime.load_config()

    configs = [(novel_dir.name, load_book_id(novel_dir)) for novel_dir in novel_dirs]

    async with runtime.async_playwright() as playwright:
        browser, context = await runtime.create_context(playwright, headless=True)
        page = await context.new_page()
        try:
            if not await runtime.goto_with_login_retry(page, "https://fanqienovel.com/writer/zone/"):
                raise DataProbeError("saved session cannot open writer zone")
            await runtime.settle_page(page)

            yesterday = (date.today() - timedelta(days=1)).isoformat()
            report = {}
            for slug, book_id in configs:
                report[slug] = {
                    "book_id": book_id,
                    "book_list": summarize(
                        "book_list",
                        await get_json(page, "/api/author/book/book_list/v0", {"page_index": 0, "page_count": 50}),
                    ),
                    "chapter_stats": summarize(
                        "chapter_stats",
                        await get_json(
                            page,
                            "/api/author/stats/chapter_list_v1/v0/",
                            {"book_id": book_id, "page_index": 0, "page_count": 200},
                        ),
                    ),
                    "single_common": summarize(
                        "single_common",
                        await get_json(page, "/api/author/sa_stats/single_common/v0/", {"book_id": book_id}),
                    ),
                    "single_by_date": summarize(
                        "single_by_date",
                        await get_json(
                            page,
                            "/api/author/sa_stats/single_by_date/v0/",
                            {"book_id": book_id, "start_date": yesterday, "end_date": yesterday},
                        ),
                    ),
                }

            links = await page.locator("a").evaluate_all(
                "els => els.map(a => ({text:(a.innerText||'').trim(), href:a.href||''}))"
            )
            report["navigation"] = [
                {"text": item["text"], "href": item["href"]}
                for item in links
                if item.get("text") and any(word in item["text"] for word in ("数据", "收益", "分析", "收入", "稿费"))
            ][:30]

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
        return asyncio.run(run([path.resolve() for path in args.novel_dirs], args.runtime))
    except (fanqie_probe.ProbeError, DataProbeError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
