# coding: utf-8
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "novels" / "walk-to-earn" / "chapters"
AUDIT = ROOT / "novels" / "walk-to-earn" / "audits" / "quality-diagnostic-131-140-20260914.md"


def body_chars(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        text = "\n".join(lines[1:])
    return len(re.sub(r"\s+", "", text))


def run(label: str, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    out = proc.stdout or ""
    print(f"[{label}] exit={proc.returncode}")
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    return proc.returncode, out


def main() -> int:
    counts: dict[int, int] = {}
    for n in range(131, 141):
        counts[n] = body_chars(CHAPTER_DIR / f"chapter-{n}.md")

    chapters = [str(p) for p in sorted(CHAPTER_DIR.glob("chapter-*.md"), key=lambda p: int(p.stem.split("-")[-1]))]
    commands: list[tuple[str, list[str]]] = [
        ("template_markers", [sys.executable, "novels/walk-to-earn/tools/check_template_markers.py"]),
        ("protected_invariants", [sys.executable, "novels/walk-to-earn/tools/check_rebuild_invariants.py"]),
        ("novel_gate", [sys.executable, "shared/tools/novel_gate.py", *chapters]),
        ("prose_guard", [sys.executable, "shared/tools/prose_guard.py", *chapters]),
        ("chapter_length_gate", [sys.executable, "novels/walk-to-earn/tools/audit_chapter_lengths.py", "--minimum", "2000", "--fail"]),
        ("five_chapter_release_floor", [sys.executable, "novels/walk-to-earn/tools/check_release_floor.py", "--start", "61", "--minimum", "9999", "--normal", "5", "--maximum", "5", "--require-all"]),
    ]

    results: list[tuple[str, int, str]] = []
    for label, args in commands:
        code, out = run(label, args)
        results.append((label, code, out))

    prose_out = next((out for label, _, out in results if label == "prose_guard"), "")
    prose_hard_lines = [line for line in prose_out.splitlines() if line.startswith("HARD") or line.lstrip().startswith("↳")]

    lines = [
        "# Walk to Earn quality diagnostic — chapters 131–140 — 2026-09-14",
        "",
        "This is a quality-only diagnostic. It does not resolve the Fanqie runtime and performs no platform mutation.",
        "",
        "## Exact non-whitespace body counts",
        "",
        "| Chapter | Count | >=2000 |",
        "| ---: | ---: | :---: |",
    ]
    for n in range(131, 141):
        lines.append(f"| {n} | {counts[n]} | {'PASS' if counts[n] >= 2000 else 'FAIL'} |")
    lines.extend([
        "",
        f"- 131–135 total: **{sum(counts[n] for n in range(131, 136))}** — {'PASS' if sum(counts[n] for n in range(131, 136)) > 9999 else 'FAIL'} (>9999 required)",
        f"- 136–140 total: **{sum(counts[n] for n in range(136, 141))}** — {'PASS' if sum(counts[n] for n in range(136, 141)) > 9999 else 'FAIL'} (>9999 required)",
        "",
        "## Prose hard hits",
        "",
        "```text",
        "\n".join(prose_hard_lines) if prose_hard_lines else "(none)",
        "```",
        "",
        "## Gate results",
        "",
    ])
    for label, code, out in results:
        lines.append(f"### {label}: {'PASS' if code == 0 else 'FAIL'} (exit {code})")
        lines.append("")
        lines.append("```text")
        trimmed = out.strip()
        if len(trimmed) > 16000:
            trimmed = trimmed[-16000:]
            trimmed = "[output truncated to last 16000 chars]\n" + trimmed
        lines.append(trimmed or "(no output)")
        lines.append("```")
        lines.append("")

    required_labels = {"template_markers", "protected_invariants", "novel_gate", "chapter_length_gate", "five_chapter_release_floor"}
    all_ok = all(code == 0 for label, code, _ in results if label in required_labels)
    local_ok = all(counts[n] >= 2000 for n in range(131, 141)) and sum(counts[n] for n in range(131,136)) > 9999 and sum(counts[n] for n in range(136,141)) > 9999
    lines.extend([
        "## Diagnostic verdict",
        "",
        f"- automated gates: **{'PASS' if all_ok else 'FAIL'}**",
        f"- 131–140 local length checks: **{'PASS' if local_ok else 'FAIL'}**",
        "- This diagnostic alone is not publishing approval; cold-read review remains required.",
        "",
    ])
    AUDIT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
