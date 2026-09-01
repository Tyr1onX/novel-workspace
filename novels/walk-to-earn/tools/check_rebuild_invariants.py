#!/usr/bin/env python3
"""Hard continuity checks for protected Walk to Earn facts.

The author explicitly requested a data-driven cold-start rewrite of chapters
1-10 on 2026-09-01. The opening anchors below therefore follow the approved
new chapter mapping, while chapters 11-40 keep their existing protected facts.
Continuation at 41+ remains allowed.
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
    expected = [CHAPTERS / f"chapter-{i:03d}.md" for i in range(1, 41)]
    for path in expected:
        if not path.exists():
            FAILURES.append(f"missing expected baseline chapter: {path.name}")

    # Rebuilt cold start: protect the facts, numbers and new chapter mapping.
    require(1, "5031", "201.24", "0.04", "7.3公里", "20018", "800.72")
    require(2, "699", "20.4公里", "100公里", "0.05元 / 有效步")
    require(3, "13762", "550.48")
    require(4, "14863", "594.52", "6.4公里")
    require(5, "21864", "874.56", "55.3公里")
    require(6, "6047", "241.88", "59.1公里")
    require(7, "13742", "549.68", "68.2公里")
    require(8, "3.6公里", "10843", "433.72")
    require(9, "18642", "745.68", "96.8公里")
    require(10, "100.1公里", "0.05元 / 有效步", "500公里", "20137", "962.85", "111.9公里")

    # Shared-memory anchor used again in chapter 32.
    require(11, "42", "昨天你帮我买")
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

    # Time-purchase chapter.
    require(35, "74.2元", "3.3V", "5V", "做梦都在接他们电话")

    # Body remains ordinary.
    require(38, "7秒5", "2米24", "4分06", "四分十四", "4分42", "4分23", "603.6公里")
    forbid(38, "系统强化", "身体强化", "体质强化")

    # Family scene and protected V2 close.
    require(39, "327元")
    require(40, "七公里", "17683", "1414.64", "628.4公里", "0.08元 / 有效步", "1500公里", "0.12元 / 有效步")
    forbid(40, "青禾河", "露天电影", "手机11%", "手机2%")

    # First continuation window anchors, when present.
    if (CHAPTERS / "chapter-041.md").exists():
        require(41, "18322", "1465.76", "栖湾")
    if (CHAPTERS / "chapter-042.md").exists():
        require(42, "21405", "1712.40", "十八")
    if (CHAPTERS / "chapter-043.md").exists():
        require(43, "7231", "578.48", "663.6公里", "澄光科技园")

    if FAILURES:
        print("WALK CONTINUITY INVARIANTS: FAIL")
        for failure in FAILURES:
            print(f"- {failure}")
        return 1

    print("WALK CONTINUITY INVARIANTS: PASS")
    print("- rebuilt chapters 001-010 anchors present")
    print("- protected chapters 011-040 anchors present")
    print("- protected numeric/mechanic/continuity anchors present")
    print("- audited continuation at chapter 041+ is allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
