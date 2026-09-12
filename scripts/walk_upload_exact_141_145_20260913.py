# coding: utf-8
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "7677956141673892926"
START = 141
END = 145
SCHEDULE = "2026-09-22"
SUMMARY_RE = re.compile(r"成功:\s*(\d+)\s+失败:\s*(\d+)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()

    command = [
        sys.executable,
        str(ROOT / "shared" / "tools" / "fanqie_runtime_bridge.py"),
        "--runtime",
        args.runtime,
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
        f"{START}-{END}",
        "--schedule",
        SCHEDULE,
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
        raise RuntimeError(f"publisher exited with code {proc.returncode}")
    if "已取消" in output:
        raise RuntimeError("publisher cancelled before confirmed upload")
    matches = list(SUMMARY_RE.finditer(output))
    if not matches:
        raise RuntimeError("publisher did not emit success summary")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if success != 5 or failed != 0:
        raise RuntimeError(f"publisher summary mismatch: success={success} failed={failed}")

    print(
        f"CONFIRMED_UPLOAD chapters={START}-{END} schedule={SCHEDULE} "
        f"success={success} failed={failed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
