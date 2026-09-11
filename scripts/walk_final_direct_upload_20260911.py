# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "7677956141673892926"
SUMMARY_RE = re.compile(r"成功:\s*(\d+)\s+失败:\s*(\d+)")
STAGES = {
    "create1direct": (131, 160),
    "create2direct": (161, 185),
}


def schedule_for(chapter: int) -> str:
    if chapter < 111 or chapter > 185:
        raise ValueError(f"chapter out of September closeout range: {chapter}")
    base = dt.date(2026, 9, 16)
    return (base + dt.timedelta(days=(chapter - 111) // 5)).isoformat()


def run_group(runtime: str, start: int, end: int) -> None:
    if end - start + 1 != 5 or (start - 111) % 5 != 0:
        raise ValueError(f"unsafe group boundary: {start}-{end}")
    schedule = schedule_for(start)
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
        raise RuntimeError(f"publisher exited with code {proc.returncode} for chapters {start}-{end}")
    if "已取消" in output:
        raise RuntimeError(f"publisher cancelled before confirmed upload for chapters {start}-{end}")
    matches = list(SUMMARY_RE.finditer(output))
    if not matches:
        raise RuntimeError(f"publisher did not emit success summary for chapters {start}-{end}")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if success != 5 or failed != 0:
        raise RuntimeError(
            f"publisher summary mismatch for {start}-{end}: expected success=5 failed=0, "
            f"got success={success} failed={failed}"
        )
    print(
        f"CONFIRMED_UPLOAD chapters={start}-{end} schedule={schedule} success={success} failed={failed}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    first, last = STAGES[args.stage]
    for start in range(first, last + 1, 5):
        run_group(args.runtime, start, start + 4)
    print(f"CONFIRMED_DIRECT_STAGE stage={args.stage} chapters={first}-{last}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
