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


def run_upload(runtime: str, chapters: str, schedule: str, expected: int) -> None:
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
        chapters,
        "--schedule",
        schedule,
        "--per-day",
        "5",
        "--time",
        "00:00",
        "--use-ai",
        "--headless",
    ]
    print("$ " + subprocess.list2cmdline(command))
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
    print(output, end="" if output.endswith("\n") else "\n")
    if proc.returncode != 0:
        raise RuntimeError(f"publisher exited with code {proc.returncode} for chapters {chapters}")
    if "已取消" in output:
        raise RuntimeError(f"publisher cancelled before confirmed upload for chapters {chapters}")
    matches = list(SUMMARY_RE.finditer(output))
    if not matches:
        raise RuntimeError(f"publisher did not emit success summary for chapters {chapters}")
    success = int(matches[-1].group(1))
    failed = int(matches[-1].group(2))
    if success != expected or failed != 0:
        raise RuntimeError(
            f"publisher summary mismatch for {chapters}: expected success={expected}, got success={success}, failed={failed}"
        )
    print(f"CONFIRMED_UPLOAD chapters={chapters} schedule={schedule} success={success} failed={failed}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    run_upload(args.runtime, "117-120", "2026-09-17", 4)
    run_upload(args.runtime, "121-185", "2026-09-18", 65)
    print("CONFIRMED_RECOVERY_UPLOAD_COMPLETE chapters=117-185")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
