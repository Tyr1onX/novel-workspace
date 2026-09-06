#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import fanqie_compat
import fanqie_sync

NOVEL = Path("novels/death-list")
S = NOVEL / "platform-sync"
TITLE = "每天零点我都会收到一份死亡名单"
EXPECTED = list(range(1, 10))


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def numbered_rows(report):
    return [
        row for row in report.get("remote_items", [])
        if isinstance(row.get("chapter_number"), int)
    ]


def assert_exact_existing(report):
    rows = numbered_rows(report)
    nums = sorted(row["chapter_number"] for row in rows)
    if nums != EXPECTED:
        raise RuntimeError(f"expected exact remote chapters 1-9, got {nums}")
    diff = report.get("differences") or {}
    for key in (
        "local_only_chapters",
        "remote_only_chapters",
        "title_mismatches",
        "duplicate_remote_chapter_numbers",
        "position_mismatches",
    ):
        if diff.get(key):
            raise RuntimeError(f"reconcile mismatch {key}: {diff.get(key)}")
    return rows


def preflight(path):
    report = load(path)
    remote = report.get("remote") or {}
    if remote.get("item_count") == 0 and remote.get("numbered_item_count") == 0:
        print("empty")
        return 0
    rows = assert_exact_existing(report)
    bad = [
        (row["chapter_number"], row.get("status"))
        for row in rows
        if row.get("status") not in {"scheduled", "reviewing", "published"}
    ]
    if bad:
        raise RuntimeError(f"unexpected existing statuses: {bad}")
    print("existing")
    return 0


def ready(path):
    rows = assert_exact_existing(load(path))
    reviewing = sorted(
        row["chapter_number"] for row in rows if row.get("status") == "reviewing"
    )
    if reviewing:
        print("REVIEW_PENDING chapters=" + ",".join(map(str, reviewing)))
        return 3
    bad = [
        (row["chapter_number"], row.get("status"))
        for row in rows
        if row.get("status") not in {"scheduled", "published"}
    ]
    if bad:
        raise RuntimeError(f"chapters are not publish-ready: {bad}")
    print("PUBLISH_READY")
    return 0


def classify(code):
    one = load(S / "one-shot.json")
    result = one.get("result") or {}
    if code == 0 and result.get("platform_status") == "success":
        print("success")
        return 0
    message = str(result.get("message") or "")
    period = r"(每日|当日|今日|本日|单日|今天|每月|本月|单月|月度)"
    limit = r"(上限|限制|限额|额度|已达|达到|超出|超过)"
    if re.search(period + r"[^，。;；]{0,24}" + limit, message) or re.search(
        limit + r"[^，。;；]{0,24}" + period, message
    ):
        print("daily_limit")
        return 0
    raise RuntimeError(
        f"publish-now non-limit failure: code={code}, message={message!r}"
    )


def final(path, publish_result):
    rows = assert_exact_existing(load(path))
    bad = [
        (row["chapter_number"], row.get("status"))
        for row in rows
        if row.get("status") not in {"published", "scheduled"}
    ]
    if bad:
        raise RuntimeError(f"unexpected final statuses: {bad}")

    published = sorted(
        row["chapter_number"] for row in rows if row.get("status") == "published"
    )
    scheduled = sorted(
        row["chapter_number"] for row in rows if row.get("status") == "scheduled"
    )
    if publish_result == "success" and scheduled:
        raise RuntimeError(f"publisher said success but still scheduled {scheduled}")
    if publish_result == "daily_limit" and not scheduled:
        publish_result = "success"

    completed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    launch_result = {
        "version": 1,
        "book_title": TITLE,
        "completed_at": completed_at,
        "requested_chapters": EXPECTED,
        "published_chapters": published,
        "still_scheduled_chapters": scheduled,
        "publish_result": publish_result,
        "verified_by_read_only_reconcile": True,
    }
    (S / "launch-result.json").write_text(
        json.dumps(launch_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    one = load(S / "one-shot.json")
    one.update(
        {
            "status": "completed",
            "completed_at": completed_at,
            "result": {
                "platform_status": "published" if not scheduled else "partial_daily_limit",
                "published_chapters": published,
                "still_scheduled_chapters": scheduled,
            },
        }
    )
    (S / "one-shot.json").write_text(
        json.dumps(one, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    queue = load(S / "queue.json")
    for operation in queue.get("operations", []):
        if operation.get("id") == "death-list-create-001-009-20260906":
            operation["status"] = "completed"
            operation["completed_at"] = completed_at
    queue["updated_at"] = completed_at
    (S / "queue.json").write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    fanqie_compat.install_compat()
    _config, _policy, _queue, local = fanqie_sync.load_model(NOVEL.resolve())
    state = load(S / "sync-state.json")
    state["last_sync_at"] = completed_at
    state["remote_snapshot_at"] = completed_at
    state["chapters"] = {
        str(n): {
            "local_sha256": local[n].digest,
            "last_action": "create",
            "last_synced_at": completed_at,
            "queue_operation_id": "death-list-create-001-009-20260906",
        }
        for n in EXPECTED
    }
    (S / "sync-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(launch_result, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd", required=True)
    for name in ("preflight", "ready"):
        sub = subs.add_parser(name)
        sub.add_argument("report")
    sub = subs.add_parser("classify")
    sub.add_argument("code", type=int)
    sub = subs.add_parser("final")
    sub.add_argument("report")
    sub.add_argument("result", choices=("success", "daily_limit"))
    args = parser.parse_args()
    try:
        if args.cmd == "preflight":
            return preflight(args.report)
        if args.cmd == "ready":
            return ready(args.report)
        if args.cmd == "classify":
            return classify(args.code)
        return final(args.report, args.result)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
