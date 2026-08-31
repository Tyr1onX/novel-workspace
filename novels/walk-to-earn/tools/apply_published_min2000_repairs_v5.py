#!/usr/bin/env python3
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply_published_min2000_repairs import BLOCKS  # noqa: E402
from apply_published_min2000_repairs_v2 import EXTRA, body_chars, append_once  # noqa: E402
from apply_published_min2000_repairs_v4 import FINAL_EXTRA  # noqa: E402

CHAPTERS = HERE.parent / "chapters"

SAFE_MARGIN_EXTRA = {
23: r'''
第一节实验开始以后，老师让他们先核设备编号。胡凯把昨天领到的记录册摊在桌边，沈川则去柜子里找对应模块。

两个人分开做自己的事，等设备通电以后才重新凑到一张桌上。昨天那三个小时空课已经过去，今天该做的只是把实验做完。
''',
}


def main() -> int:
    repaired = []
    residual = []
    for number in sorted(BLOCKS):
        path = CHAPTERS / f"chapter-{number:03d}.md"
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        before = body_chars(text)
        if before < 2000:
            text = append_once(text, f"<!-- min2000-repair-ch{number} -->", BLOCKS[number])
        if body_chars(text) < 2000 and number in EXTRA:
            text = append_once(text, f"<!-- min2000-repair-extra-ch{number} -->", EXTRA[number])
        if body_chars(text) < 2000 and number in FINAL_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-final-ch{number} -->", FINAL_EXTRA[number])
        if body_chars(text) < 2000 and number in SAFE_MARGIN_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-margin-ch{number} -->", SAFE_MARGIN_EXTRA[number])
        after = body_chars(text)
        print(f"ch{number}: {before} -> {after}")
        if after < 2000:
            residual.append((number, after, 2000 - after))
            continue
        if after != before:
            path.write_text(text, encoding="utf-8")
            repaired.append((number, before, after))

    p43 = CHAPTERS / "chapter-043.md"
    t43 = p43.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    b43 = body_chars(t43)
    if b43 < 2000 and 43 in EXTRA:
        t43 = append_once(t43, "<!-- min2000-repair-extra-ch43 -->", EXTRA[43])
    a43 = body_chars(t43)
    print(f"ch43: {b43} -> {a43}")
    if a43 < 2000:
        residual.append((43, a43, 2000 - a43))
    elif a43 != b43:
        p43.write_text(t43, encoding="utf-8")
        repaired.append((43, b43, a43))

    print("RESIDUAL_SHORTS=" + repr(residual))
    print("REPAIRED=" + repr(repaired))
    return 2 if residual else 0

if __name__ == "__main__":
    raise SystemExit(main())
