#!/usr/bin/env python3
"""Publish one already-scheduled Fanqie chapter immediately.

This is intentionally narrower than the normal publisher:
- the target must already exist on Fanqie;
- the target must be the explicitly authorized chapter in one-shot.json;
- audit.status must be passed;
- only a currently scheduled/pending chapter is mutated;
- the operation is idempotent: an already-published target is treated as done;
- after submit, the chapter-management page is read again and the result is recorded.

The script does not create chapters, edit title/body text, delete chapters, or touch any
other schedule entry.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fanqie_probe
import fanqie_sync


class PublishNowError(RuntimeError):
    pass


def _load_runtime(runtime_dir: Path):
    script = runtime_dir / "fanqie_upload.py"
    if not script.is_file():
        raise PublishNowError(f"Fanqie runtime script not found: {script}")
    spec = importlib.util.spec_from_file_location("fanqie_runtime_publish_now", script)
    if spec is None or spec.loader is None:
        raise PublishNowError(f"Cannot load Fanqie runtime: {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_request(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishNowError(f"cannot read request {path}: {exc}") from exc
    if data.get("version") != 1:
        raise PublishNowError("one-shot request version must be 1")
    if data.get("action") != "publish_now":
        raise PublishNowError("one-shot action must be publish_now")
    if data.get("authorized") is not True:
        raise PublishNowError("publish_now requires authorized=true")
    if (data.get("audit") or {}).get("status") != "passed":
        raise PublishNowError("publish_now requires audit.status=passed")
    if data.get("status") not in {None, "pending", "completed"}:
        raise PublishNowError(f"unsupported one-shot status: {data.get('status')!r}")
    chapter = data.get("chapter")
    if not isinstance(chapter, int) or chapter < 1:
        raise PublishNowError("publish_now chapter must be a positive integer")
    return data


def _write_request(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _status_text(row: dict[str, Any]) -> str:
    return str(row.get("status") or "").strip()


async def _read_chapter_table(runtime, page, book_id: str) -> list[dict[str, Any]]:
    url = runtime.CHAPTER_MANAGE_URL_TPL.format(book_id=book_id)
    if hasattr(runtime, "goto_with_login_retry"):
        ok = await runtime.goto_with_login_retry(page, url)
        if not ok:
            raise PublishNowError("saved Fanqie login has expired")
    else:
        await page.goto(url)
        if "/login" in (page.url or ""):
            raise PublishNowError("saved Fanqie login has expired")
    try:
        await page.wait_for_load_state("networkidle", timeout=getattr(runtime, "NETWORKIDLE_MS", 3000))
    except Exception:
        pass
    try:
        await page.wait_for_selector("tr td", timeout=getattr(runtime, "_browser_timeout", 15000))
    except Exception as exc:
        raise PublishNowError(f"chapter-management table did not load: {exc}") from exc
    chapters, _last = await runtime.extract_chapters_from_page(page, book_id)
    return chapters


def _find_numbered(chapters: list[dict[str, Any]], chapter_number: int) -> dict[str, Any] | None:
    matches = [row for row in chapters if row.get("chapterNum") == chapter_number]
    if len(matches) > 1:
        raise PublishNowError(f"platform has duplicate chapter number {chapter_number}; refusing mutation")
    return matches[0] if matches else None


async def _switch_timer_off(runtime, page) -> str:
    result = await page.evaluate(
        """() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
            while (walker.nextNode()) {
                const text = (walker.currentNode.textContent || '').trim();
                if (!text.includes('定时发布')) continue;
                let parent = walker.currentNode.parentElement;
                for (let i = 0; i < 6 && parent; i++, parent = parent.parentElement) {
                    const sw = parent.querySelector('button[role="switch"]');
                    if (!sw) continue;
                    const before = sw.getAttribute('aria-checked');
                    if (before === 'true') sw.click();
                    return before === 'true' ? 'clicked_off' : 'already_off';
                }
            }
            return 'not_found';
        }"""
    )
    if result == "not_found":
        raise PublishNowError("cannot find the Fanqie scheduled-publish switch")
    await page.wait_for_timeout(600)
    # Re-check instead of trusting a click on a React control.
    still_on = await page.evaluate(
        """() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
            while (walker.nextNode()) {
                const text = (walker.currentNode.textContent || '').trim();
                if (!text.includes('定时发布')) continue;
                let parent = walker.currentNode.parentElement;
                for (let i = 0; i < 6 && parent; i++, parent = parent.parentElement) {
                    const sw = parent.querySelector('button[role="switch"]');
                    if (sw) return sw.getAttribute('aria-checked') === 'true';
                }
            }
            return null;
        }"""
    )
    if still_on is True:
        raise PublishNowError("scheduled-publish switch remained enabled after click")
    return result


async def _publish_existing_now(runtime, page, row: dict[str, Any], *, use_ai: bool) -> None:
    edit_url = row.get("editUrl")
    if not edit_url:
        raise PublishNowError("target chapter has no edit URL on the chapter-management page")
    if str(edit_url).startswith("/"):
        edit_url = runtime.BASE_URL + str(edit_url)

    await page.goto(str(edit_url))
    await runtime.wait_for_editor_ready(page, draft_action="放弃")
    if hasattr(runtime, "dismiss_edit_hint"):
        await runtime.dismiss_edit_hint(page)

    # Do not clear or fill the editor. This operation changes only the release mode.
    await runtime._navigate_to_publish_settings(
        page, use_ai=use_ai, draft_action="继续编辑"
    )
    timer_result = await _switch_timer_off(runtime, page)
    print(f"timer switch: {timer_result}")

    if hasattr(runtime, "_check_daily_limit"):
        await runtime._check_daily_limit(page)
    confirm_btn = page.locator("button", has_text="确认发布")
    if await confirm_btn.count() == 0:
        raise PublishNowError("cannot find 确认发布 button")
    await confirm_btn.first.click(
        no_wait_after=True, timeout=getattr(runtime, "_browser_timeout", 15000)
    )
    await runtime._wait_publish_result(page, confirm_btn.first)


async def _verify(runtime, page, book_id: str, chapter_number: int) -> tuple[str, dict[str, Any]]:
    # The table can briefly show 审核中 after a successful immediate-submit. Both
    # 已发布 and 审核中 prove it is no longer in the scheduled queue. Keep polling a
    # little while so the usual fast path resolves to 已发布.
    last_row: dict[str, Any] | None = None
    for attempt in range(6):
        rows = await _read_chapter_table(runtime, page, book_id)
        row = _find_numbered(rows, chapter_number)
        if not row:
            raise PublishNowError(f"chapter {chapter_number} disappeared after submit")
        last_row = row
        status = _status_text(row)
        if "已发布" in status:
            return "published", row
        if "审核中" in status:
            if attempt < 5:
                await page.wait_for_timeout(5000)
                continue
            return "reviewing", row
        if "待发布" in status:
            if attempt < 5:
                await page.wait_for_timeout(3000)
                continue
            raise PublishNowError("submit returned, but chapter is still 待发布")
        if attempt < 5:
            await page.wait_for_timeout(3000)
    raise PublishNowError(f"unrecognized post-submit status: {_status_text(last_row or {})}")


async def run(novel_dir: Path, runtime_arg: str | None, request_path: Path) -> int:
    config, policy, _queue, local = fanqie_sync.load_model(novel_dir)
    request = _load_request(request_path)
    chapter_number = int(request["chapter"])
    book_id = str(config["book_id"])

    if str(request.get("book_id") or book_id) != book_id:
        raise PublishNowError("one-shot book_id does not match config.json")
    if chapter_number not in local:
        raise PublishNowError(f"local chapter {chapter_number} does not exist")

    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = _load_runtime(runtime_dir)
    runtime.load_config()
    headless = bool((config.get("browser") or {}).get("headless", True))
    use_ai = bool((policy.get("declaration") or {}).get("use_ai", True))

    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=headless)
        page = await context.new_page()
        try:
            rows = await _read_chapter_table(runtime, page, book_id)
            row = _find_numbered(rows, chapter_number)
            if not row:
                raise PublishNowError(f"Fanqie does not contain chapter {chapter_number}")
            before_status = _status_text(row)
            print(
                f"target: 第{chapter_number}章 | {row.get('title')} | "
                f"status={before_status} | date={row.get('date')} {row.get('time')}"
            )

            if "已发布" in before_status:
                final_status = "published"
                verified = row
                print("target is already published; treating request as idempotently complete")
            else:
                if "待发布" not in before_status:
                    raise PublishNowError(
                        f"chapter {chapter_number} must be 待发布; actual status={before_status!r}"
                    )
                await _publish_existing_now(runtime, page, row, use_ai=use_ai)
                final_status, verified = await _verify(runtime, page, book_id, chapter_number)

            await runtime.save_auth(context)
        finally:
            await runtime.close_browser_safely(browser)

    request["status"] = "completed"
    request["completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    request["result"] = {
        "platform_status": final_status,
        "chapter": chapter_number,
        "title": verified.get("title"),
        "scheduled_date_before": row.get("date"),
        "scheduled_time_before": row.get("time"),
    }
    _write_request(request_path, request)
    print(
        f"PUBLISH_NOW_OK book_id={book_id} chapter={chapter_number} "
        f"platform_status={final_status}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish one scheduled Fanqie chapter immediately")
    parser.add_argument("novel_dir", type=Path)
    parser.add_argument("--runtime")
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        return asyncio.run(
            run(args.novel_dir.resolve(), args.runtime, args.request.resolve())
        )
    except (fanqie_probe.ProbeError, fanqie_sync.SyncError, PublishNowError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
