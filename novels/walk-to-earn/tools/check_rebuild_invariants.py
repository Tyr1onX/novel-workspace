#!/usr/bin/env python3
"""Hard continuity checks for the current Walk to Earn 1-40 rebuild.

This is intentionally narrow. It protects facts that have already caused
regressions during large language/style rewrites. It does not judge prose
quality; the shared novel guards and manual cold read do that.
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "chapters"


FAILURES: list[str] = []


def read(chapter: int) -> str:
    path = CHAPTERS / f"chapter-{chapter:03d}.md"
    if not path.exists():
        FAILURES.append(f"missing chapter file: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def require(chapter: int, *tokens: str) -> None:
    text = read(chapter)
    for token in tokens:
        if token not in text:
            FAILURES.append(f"chapter-{chapter:03d}: missing required anchor {token!r}")


def forbid(chapter: int, *tokens: str) -> None:
    text = read(chapter)
    for token in tokens:
        if token in text:
            FAILURES.append(f"chapter-{chapter:03d}: forbidden stale anchor still present {token!r}")


def main() -> int:
    # The audited freeze is exactly chapters 1-40. Do not silently continue.
    expected = [CHAPTERS / f"chapter-{i:03d}.md" for i in range(1, 41)]
    for path in expected:
        if not path.exists():
            FAILURES.append(f"missing expected chapter: {path.name}")
    if (CHAPTERS / "chapter-041.md").exists():
        FAILURES.append("chapter-041.md exists while the 1-40 audit freeze is active")

    # Opening/mechanic anchors.
    require(1, "5031", "201.24", "0.04", "7.3公里")
    require(2, "20018", "800.72")
    require(3, "699", "100公里", "0.05元/步")
    require(10, "100.1公里", "0.05元/步", "500公里")

    # Shared-memory anchor used again in chapter 32.
    require(11, "42", "昨天你给我带")
    require(32, "四十二", "展馆")

    # Long-distance progression and recovery anchors.
    require(27, "16837", "841.85", "342.1公里", "二十八公里")
    require(28, "19.8公里", "27126", "1356.30", "369.1公里")
    require(29, "179", "22184", "1109.20", "390.7公里", "9880", "494.00", "398.1公里")
    require(30, "第一次", "38642", "1932.10", "436.4公里")
    require(31, "4486", "224.30", "439.6公里", "6.3公里", "13714", "455.6公里")

    # 500km upgrade must remain private from Zhou Hang and use only the one system.
    require(33, "500.1公里", "0.08元 / 有效步", "1500公里", "0.12元 / 有效步")
    forbid(33, "八分了啊", "那今天搬这些东西也给你算步数")

    # First complete ordinary day at the 0.08 tier.
    require(34, "12742", "1019.36", "637.10", "0.08元 / 有效步")

    # Time-purchase chapter: exact taxi price, correct module mismatch, and Zhou Hang's post-internship call residue.
    require(35, "74.2元", "3.3V", "5V", "做梦都在接他们电话")

    # Body remains ordinary; preserve measured results rather than supernatural enhancement claims.
    require(38, "7秒5", "2米24", "4分06", "4分14", "4分42", "4分23", "603.6公里")
    forbid(38, "系统强化", "身体强化", "体质强化")

    # Family scene and final stage close.
    require(39, "327元")
    require(40, "七公里", "17683", "1414.64", "628.4公里", "0.08元 / 有效步", "1500公里", "0.12元 / 有效步")
    forbid(40, "青禾河", "露天电影", "手机11%", "手机2%")

    if FAILURES:
        print("WALK REBUILD INVARIANTS: FAIL")
        for failure in FAILURES:
            print(f"- {failure}")
        return 1

    print("WALK REBUILD INVARIANTS: PASS")
    print("- chapters 001-040 present; chapter 041 absent")
    print("- protected numeric/mechanic/continuity anchors present")
    print("- stale chapter-33 secret-leak and chapter-40 old-route anchors absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
