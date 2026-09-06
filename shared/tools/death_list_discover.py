#!/usr/bin/env python3
import argparse, asyncio, importlib.util
from pathlib import Path

TITLE = "每天零点我都会收到一份死亡名单"
OUT = Path("novels/death-list/platform-sync/.discovered-book-id")

async def run(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    spec = importlib.util.spec_from_file_location("fanqie_death_list_discovery", script)
    if not script.is_file() or spec is None or spec.loader is None:
        raise RuntimeError(f"invalid Fanqie runtime: {script}")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    runtime.load_config()
    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=True)
        page = await context.new_page()
        try:
            if not await runtime.goto_with_login_retry(page, runtime.BOOK_MANAGE_URL):
                raise RuntimeError("saved Fanqie login cannot open book management")
            await runtime.settle_page(page)
            result = await page.evaluate("""async () => {
              const u = new URL('/api/author/book/book_list/v0', location.origin);
              u.searchParams.set('page_index','0'); u.searchParams.set('page_count','50');
              const r = await fetch(u.toString(), {credentials:'include'});
              return {status:r.status, body:await r.json()};
            }""")
            if result.get("status") != 200:
                raise RuntimeError(f"book list HTTP {result.get('status')}")
            body = result.get("body") or {}
            data = body.get("data", body) if isinstance(body, dict) else {}
            rows = data.get("book_list", []) if isinstance(data, dict) else []
            matches = [r for r in rows if isinstance(r, dict) and str(r.get("book_name") or "").strip() == TITLE]
            if len(matches) != 1:
                raise RuntimeError(f"expected one exact-title book, found {len(matches)}")
            book_id = str(matches[0].get("book_id") or "").strip()
            if not book_id.isdigit():
                raise RuntimeError("exact-title book has no numeric id")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(book_id, encoding="utf-8")
            await runtime.save_auth(context)
            print("EXACT_BOOK_OK")
        finally:
            await runtime.close_browser_safely(browser)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runtime", type=Path, required=True)
    try: asyncio.run(run(ap.parse_args().runtime.resolve()))
    except Exception as e: print(f"ERROR: {e}"); raise SystemExit(2)
