# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "7677956141673892926"
CHAPTER = 136
SCHEDULE_DATE = "2026-09-21"
AUDIT = ROOT / "novels" / "walk-to-earn" / "audits" / "publisher-probe-136-20260914.md"
SUMMARY_RE = re.compile(r"成功:\s*(\d+)\s+失败:\s*(\d+)")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_schedule(chapter: int) -> str:
    base = dt.date(2026, 9, 16)
    day = base + dt.timedelta(days=(chapter - 111) // 5)
    return f"{day.isoformat()}T00:00+08:00"


def validate_report(path: Path, expected_max: int) -> None:
    report = load(path)
    if str(report.get("book_id")) != BOOK_ID:
        raise SystemExit("book_id mismatch")
    local = report.get("local") or {}
    remote = report.get("remote") or {}
    diff = report.get("differences") or {}
    if local.get("chapter_count") != 185 or local.get("min_chapter") != 1 or local.get("max_chapter") != 185:
        raise SystemExit(f"unexpected local chapter set: {local}")
    if remote.get("numbered_item_count") != expected_max or remote.get("min_chapter") != 1 or remote.get("max_chapter") != expected_max:
        raise SystemExit(f"unexpected remote prefix: {remote}; expected 1-{expected_max}")
    if diff.get("remote_only_chapters"):
        raise SystemExit(f"remote-only chapters: {diff['remote_only_chapters']}")
    if diff.get("duplicate_remote_chapter_numbers"):
        raise SystemExit(f"duplicate remote numbers: {diff['duplicate_remote_chapter_numbers']}")
    expected_local_only = list(range(expected_max + 1, 186))
    actual_local_only = list(diff.get("local_only_chapters") or [])
    if actual_local_only != expected_local_only:
        raise SystemExit(f"unexpected local-only chapters: {actual_local_only}; expected {expected_local_only}")
    bad_positions = [row for row in (diff.get("position_mismatches") or []) if int(row.get("chapter") or -1) not in {23, 24}]
    if bad_positions:
        raise SystemExit(f"unexpected position mismatches: {bad_positions}")
    if diff.get("title_mismatches"):
        raise SystemExit(f"title mismatches remain: {diff['title_mismatches']}")
    by_num = {}
    for row in report.get("remote_items") or []:
        n = row.get("chapter_number")
        if isinstance(n, int):
            by_num[n] = row
    for n in range(111, expected_max + 1):
        row = by_num.get(n)
        if row is None:
            raise SystemExit(f"chapter {n} missing from remote_items")
        if row.get("status") not in {"scheduled", "reviewing"}:
            raise SystemExit(f"chapter {n} unexpected status: {row.get('status')}")
        exp = expected_schedule(n)
        if row.get("scheduled_at") != exp:
            raise SystemExit(f"chapter {n} schedule mismatch: {row.get('scheduled_at')} != {exp}")
    print(f"PROBE_RECONCILE_PASS remote=1-{expected_max}")


def sanitize(text: str, runtime: str) -> str:
    result = text.replace(str(ROOT), "<repo>")
    if runtime:
        result = result.replace(runtime, "<runtime>")
    return result


def write_audit(runtime: str, returncode: int, output: str, success: int | None, failed: int | None) -> None:
    clean = sanitize(output, runtime)
    lines = [
        "# Chapter 136 one-shot publisher probe — 2026-09-14",
        "",
        "This probe is intentionally limited to chapter 136. Chapters 137+ are not included.",
        "Preflight requires the remote book to be a clean numbered prefix 1-135 with the expected September schedule.",
        "",
        f"- book_id: `{BOOK_ID}`",
        f"- chapter: `{CHAPTER}`",
        f"- scheduled date: `{SCHEDULE_DATE} 00:00 Asia/Shanghai`",
        f"- publisher return code: `{returncode}`",
        f"- parsed success: `{success}`",
        f"- parsed failed: `{failed}`",
        "",
        "## Publisher output",
        "",
        "```text",
        clean.rstrip(),
        "```",
        "",
    ]
    AUDIT.write_text("\n".join(lines), encoding="utf-8")


def publish(runtime: str) -> int:
    command = [
        sys.executable,
        str(ROOT / "shared" / "tools" / "fanqie_runtime_bridge.py"),
        "--runtime",
        runtime,
        "--same-time-group-size",
        "5",
        "--same-time",
        "00:00",
        "--",
        "upload",
        str(ROOT / "novels" / "walk-to-earn" / "chapters"),
        "--book-id",
        BOOK_ID,
        "--chapters",
        str(CHAPTER),
        "--schedule",
        SCHEDULE_DATE,
        "--per-day",
        "5",
        "--time",
        "00:00",
        "--use-ai",
        "--headless",
    ]
    proc = subprocess.run(
        command,
        input="y\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    output = proc.stdout or ""
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    matches = list(SUMMARY_RE.finditer(output))
    success = failed = None
    if matches:
        success = int(matches[-1].group(1))
        failed = int(matches[-1].group(2))
    write_audit(runtime, proc.returncode, output, success, failed)
    if proc.returncode == 0 and success == 1 and failed == 0 and "已取消" not in output:
        print("PROBE_PUBLISH_CONFIRMED chapter=136 success=1 failed=0", flush=True)
        return 0
    print(f"PROBE_PUBLISH_NOT_CONFIRMED returncode={proc.returncode} success={success} failed={failed}", flush=True)
    return 2


def append_post(report_path: Path, publish_status: int) -> int:
    report = load(report_path)
    remote = report.get("remote") or {}
    diff = report.get("differences") or {}
    remote_max = remote.get("max_chapter")
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write("## Postflight\n\n")
        fh.write(f"- publisher status captured by workflow: `{publish_status}`\n")
        fh.write(f"- remote numbered item count: `{remote.get('numbered_item_count')}`\n")
        fh.write(f"- remote max chapter: `{remote_max}`\n")
        fh.write(f"- local-only chapters after attempt: `{diff.get('local_only_chapters')}`\n\n")
    if remote_max == 136:
        validate_report(report_path, 136)
        print("PROBE_FINAL_VERDICT=success_remote_136_verified")
        return 0
    if remote_max == 135:
        validate_report(report_path, 135)
        print("PROBE_FINAL_VERDICT=no_mutation_remote_still_135")
        return 2
    raise SystemExit(f"unexpected remote max after probe: {remote_max}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("assert-report")
    p.add_argument("report", type=Path)
    p.add_argument("--expected-max", type=int, required=True)
    p = sub.add_parser("publish")
    p.add_argument("--runtime", required=True)
    p = sub.add_parser("postflight")
    p.add_argument("report", type=Path)
    p.add_argument("--publish-status", type=int, required=True)
    args = parser.parse_args()
    if args.command == "assert-report":
        validate_report(args.report, args.expected_max)
        return 0
    if args.command == "publish":
        return publish(args.runtime)
    if args.command == "postflight":
        return append_post(args.report, args.publish_status)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
