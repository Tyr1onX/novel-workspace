# coding: utf-8
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "7677956141673892926"
SUMMARY_RE = re.compile(r"成功:\s*(\d+)\s+失败:\s*(\d+)")

STAGES = {
    "tail1": [
        (146, 150, "2026-09-23"),
        (151, 155, "2026-09-24"),
        (156, 160, "2026-09-25"),
    ],
    "tail2": [
        (161, 165, "2026-09-26"),
        (166, 170, "2026-09-27"),
        (171, 175, "2026-09-28"),
        (176, 180, "2026-09-29"),
        (181, 185, "2026-09-30"),
    ],
}


def upload_group(runtime: str, start: int, end: int, schedule: str) -> None:
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
        f"{start}-{end}",
        "--schedule",
        schedule,
        "--per-day",
        "5",
        "--time",
        "00:00",
        "--use-ai",
        "--headless",
    ]
    print("$ " + subprocess.list2cmdline(command), flush=True)
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
    if proc.returncode != 0:
        raise RuntimeError(f"publisher exited with code {proc.returncode} for {start}-{end}")
    if "已取消" in output:
        raise RuntimeError(f"publisher cancelled before confirmed upload for {start}-{end}")
    matches = list(SUMMARY_RE.finditer(output))
    if not matches:
        raise RuntimeError(f"publisher did not emit success summary for {start}-{end}")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if success != 5 or failed != 0:
        raise RuntimeError(f"publisher summary mismatch for {start}-{end}: success={success} failed={failed}")
    print(f"CONFIRMED_GROUP chapters={start}-{end} schedule={schedule} success=5 failed=0", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=sorted(STAGES))
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    for start, end, schedule in STAGES[args.stage]:
        upload_group(args.runtime, start, end, schedule)
    total = sum(end - start + 1 for start, end, _ in STAGES[args.stage])
    print(f"CONFIRMED_STAGE stage={args.stage} chapters={total} failed=0", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
