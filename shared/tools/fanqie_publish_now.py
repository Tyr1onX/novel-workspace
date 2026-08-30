#!/usr/bin/env python3
"""Publish already-scheduled Fanqie chapters immediately, then optionally compact schedule.

Safety properties:
- targets must already exist on Fanqie;
- the explicitly authorized request must pass audit;
- targets must be consecutive chapter numbers;
- for a new batch, targets must be exactly the first pending chapters on the platform;
- only currently scheduled/pending targets are mutated;
- already-published targets are idempotently accepted on retry;
- title/body text is never edited;
- optional reflow only changes the remaining pending schedule after every requested
  immediate release succeeds;
- platform state is read again after publishing and after reflow.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import fanqie_probe
import fanqie_runtime_bridge
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


def _requested_chapters(data: dict[str, Any]) -> list[int]:
    if "chapters" in data:
        raw = data.get("chapters")
        if not isinstance(raw, list) or not raw:
            raise PublishNowError("publish_now chapters must be a non-empty list")
        if not all(isinstance(ch, int) and ch > 0 for ch in raw):
            raise PublishNowError("publish_now chapters must contain positive integers")
        chapters = list(raw)
    else:
        chapter = data.get("chapter")
        if not isinstance(chapter, int) or chapter < 1:
            raise PublishNowError("publish_now chapter must be a positive integer")
        chapters = [chapter]

    if len(set(chapters)) != len(chapters):
        raise PublishNowError("publish_now chapters contain duplicates")
    if chapters != sorted(chapters):
        raise PublishNowError("publish_now chapters must be ascending")
    expected = list(range(chapters[0], chapters[0] + len(chapters)))
    if chapters != expected:
        raise PublishNowError("publish_now chapters must be consecutive")
    return chapters


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
    _requested_chapters(data)
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


def _pending_numbers(rows: list[dict[str, Any]]) -> list[int]:
    nums = []
    for row in rows:
        if "待发布" not in _status_text(row):
            continue
        num = row.get("chapterNum")
        if isinstance(num, int):
            nums.append(num)
    return sorted(set(nums))


def _verify_batch_precondition(rows: list[dict[str, Any]], targets: list[int]) -> None:
    target_states = {ch: _find_numbered(rows, ch) for ch in targets}
    missing = [ch for ch, row in target_states.items() if row is None]
    if missing:
        raise PublishNowError(f"Fanqie does not contain requested chapters: {missing}")

    remaining_targets = [
        ch for ch in targets
        if "已发布" not in _status_text(target_states[ch] or {})
    ]
    for ch in remaining_targets:
        status = _status_text(target_states[ch] or {})
        if "待发布" not in status:
            raise PublishNowError(
                f"chapter {ch} must be 待发布 or 已发布; actual status={status!r}"
            )

    if not remaining_targets:
        return

    pending = _pending_numbers(rows)
    if pending[: len(remaining_targets)] != remaining_targets:
        raise PublishNowError(
            "requested extra-release chapters are not the first pending chapters; "
            f"requested={remaining_targets}, first_pending={pending[:len(remaining_targets)]}"
        )


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

    # Never clear or fill the editor: this changes release mode only.
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


def _schedule_map_for_pending(
    rows: list[dict[str, Any]], start_date: str, group_size: int, exact_time: str
) -> tuple[dict[str, tuple[str, str]], dict[int, str]]:
    try:
        base = datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(exact_time, "%H:%M")
    except ValueError as exc:
        raise PublishNowError(str(exc)) from exc
    pending = [
        row for row in rows
        if "待发布" in _status_text(row) and isinstance(row.get("chapterNum"), int)
    ]
    pending.sort(key=lambda row: int(row["chapterNum"]))
    schedule_map: dict[str, tuple[str, str]] = {}
    expected: dict[int, str] = {}
    for idx, row in enumerate(pending):
        target_date = (base + timedelta(days=idx // group_size)).strftime("%Y-%m-%d")
        title = str(row.get("title") or "").strip()
        if not title:
            raise PublishNowError(f"pending chapter {row.get('chapterNum')} has no title")
        schedule_map[title] = (target_date, exact_time)
        expected[int(row["chapterNum"])] = f"{target_date} {exact_time}"
    return schedule_map, expected


def _row_date_time(row: dict[str, Any]) -> str:
    return f"{str(row.get('date') or '').strip()} {str(row.get('time') or '').strip()}".strip()


async def _reflow_remaining(runtime, page, book_id: str, policy: dict, request: dict) -> dict[str, Any]:
    reflow = request.get("reflow")
    if not reflow:
        return {"performed": False}
    if not isinstance(reflow, dict):
        raise PublishNowError("reflow must be an object")
    start_date = str(reflow.get("start_date") or "").strip()
    if not start_date:
        raise PublishNowError("reflow.start_date is required")

    schedule = policy.get("schedule") or {}
    group_size = schedule.get("group_size") or schedule.get("chapters_per_day")
    slots = schedule.get("slots") or []
    if not isinstance(group_size, int) or group_size < 1:
        raise PublishNowError("policy schedule group_size must be a positive integer")
    if len(slots) != 1:
        raise PublishNowError("extra-release reflow requires exactly one schedule slot")
    exact_time = str(slots[0])

    rows = await _read_chapter_table(runtime, page, book_id)
    schedule_map, expected = _schedule_map_for_pending(rows, start_date, group_size, exact_time)
    fanqie_runtime_bridge.patch_reschedule_noops(runtime)
    if schedule_map:
        ok, bad = await runtime.reschedule_on_manage_page(
            page,
            book_id,
            schedule_map,
            max_retries=runtime.load_config().get("max_retries", 2),
            delay=runtime.load_config().get("delay_between_chapters", 3),
            volume_texts=None,
        )
        if bad:
            raise PublishNowError(f"reflow completed with failures: success={ok}, failed={bad}")
    else:
        ok, bad = 0, 0

    verify_rows = await _read_chapter_table(runtime, page, book_id)
    mismatches = []
    for ch, wanted in expected.items():
        row = _find_numbered(verify_rows, ch)
        if not row:
            mismatches.append({"chapter": ch, "expected": wanted, "actual": "missing"})
            continue
        actual = _row_date_time(row)
        if actual != wanted:
            mismatches.append({"chapter": ch, "expected": wanted, "actual": actual})
    if mismatches:
        raise PublishNowError(f"reflow verification failed: {mismatches[:5]}")
    return {
        "performed": True,
        "start_date": start_date,
        "group_size": group_size,
        "time": exact_time,
        "pending_count": len(expected),
        "changed_or_confirmed": ok,
        "verified": True,
    }


async def run(novel_dir: Path, runtime_arg: str | None, request_path: Path) -> int:
    config, policy, _queue, local = fanqie_sync.load_model(novel_dir)
    request = _load_request(request_path)
    targets = _requested_chapters(request)
    book_id = str(config["book_id"])

    if str(request.get("book_id") or book_id) != book_id:
        raise PublishNowError("one-shot book_id does not match config.json")
    missing_local = [ch for ch in targets if ch not in local]
    if missing_local:
        raise PublishNowError(f"local chapters do not exist: {missing_local}")

    runtime_dir = fanqie_probe.resolve_runtime(runtime_arg)
    runtime = _load_runtime(runtime_dir)
    runtime.load_config()
    headless = bool((config.get("browser") or {}).get("headless", True))
    use_ai = bool((policy.get("declaration") or {}).get("use_ai", True))

    chapter_results: list[dict[str, Any]] = []
    reflow_result: dict[str, Any] = {"performed": False}
    error: Exception | None = None

    async with runtime.async_playwright() as p:
        browser, context = await runtime.create_context(p, headless=headless)
        page = await context.new_page()
        try:
            rows = await _read_chapter_table(runtime, page, book_id)
            _verify_batch_precondition(rows, targets)

            for chapter_number in targets:
                rows = await _read_chapter_table(runtime, page, book_id)
                row = _find_numbered(rows, chapter_number)
                if not row:
                    raise PublishNowError(f"Fanqie does not contain chapter {chapter_number}")
                before_status = _status_text(row)
                print(
                    f"target: 第{chapter_number}章 | {row.get('title')} | "
                    f"status={before_status} | date={row.get('date')} {row.get('time')}"
                )
                try:
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
                    chapter_results.append({
                        "chapter": chapter_number,
                        "platform_status": final_status,
                        "title": verified.get("title"),
                        "scheduled_date_before": row.get("date"),
                        "scheduled_time_before": row.get("time"),
                    })
                except Exception as exc:
                    error = exc
                    chapter_results.append({
                        "chapter": chapter_number,
                        "platform_status": "failed",
                        "title": row.get("title"),
                        "scheduled_date_before": row.get("date"),
                        "scheduled_time_before": row.get("time"),
                        "message": str(exc),
                    })
                    break

            if error is None and all(r.get("platform_status") in {"published", "reviewing"} for r in chapter_results):
                try:
                    reflow_result = await _reflow_remaining(runtime, page, book_id, policy, request)
                except Exception as exc:
                    error = exc
                    reflow_result = {"performed": True, "verified": False, "message": str(exc)}

            await runtime.save_auth(context)
        finally:
            await runtime.close_browser_safely(browser)

    request["status"] = "completed"
    request["completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    request["result"] = {
        "platform_status": "success" if error is None else "partial_or_failed",
        "chapters": chapter_results,
        "reflow": reflow_result,
    }
    if error is not None:
        request["result"]["message"] = str(error)
    _write_request(request_path, request)

    if error is not None:
        print(f"PUBLISH_NOW_INCOMPLETE book_id={book_id} targets={targets} error={error}")
        return 2
    print(f"PUBLISH_NOW_OK book_id={book_id} chapters={targets} reflow={reflow_result.get('performed')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish scheduled Fanqie chapter(s) immediately")
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
