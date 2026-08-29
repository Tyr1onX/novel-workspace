#!/usr/bin/env python3
"""One-shot exact documentation finalizer for the 2026-08-29 meta audit."""

from pathlib import Path

PATCHES = {
    Path("shared/RULES.md"): [
        (
            "所有小说正文、试写章节和大幅改稿必须同时遵守：\n\n> `shared/PROSE_RULES.md`\n\n强制流程是：读取当前小说自己的风格/连续性规则与本文件 → 读取 `shared/PROSE_RULES.md` → 写第一稿 → 运行 prose scan → 人工复核高风险命中 → 再交付或提交正文。\n\n不能只因为章节卡和爽点结构通过，就跳过语言层检查；也不能为了“去 AI 味”机械碎句、批量换同义词或清除正常文学表达。",
            "所有小说正文、试写章节和大幅改稿必须同时遵守：\n\n> `shared/PROSE_RULES.md`\n>\n> `shared/META_NARRATIVE_RULES.md`\n\n强制流程是：读取当前小说自己的风格/连续性规则与本文件 → 读取 `shared/PROSE_RULES.md` 与 `shared/META_NARRATIVE_RULES.md` → 写第一稿 → 运行 prose scan 与 meta-narrative scan → 人工复核全部高风险命中 → 再交付或提交正文。\n\n至少运行：\n\n```bash\npython shared/tools/prose_guard.py <chapter.md>\npython shared/tools/meta_narrative_guard.py <chapter.md>\n```\n\n元叙事扫描的 `HARD` 必须为 0；`WARN` 必须逐条人工确认。不能只因为章节卡和爽点结构通过，就跳过语言层检查；也不能为了“去 AI 味”机械碎句、批量换同义词或清除正常文学表达。",
        ),
    ],
    Path("novels/endless-rail/docs/audit-087-106.md"): [
        (
            "# 第87～106章写作与全量审计报告\n",
            "# 第87～106章写作与全量审计报告\n\n> **状态更新（2026-08-29）：本报告最初的“全量审计通过”结论因漏检元叙事/第四面墙泄露而失效。正文已随后进行第1～106章全量重扫与修复；该维度的有效验收结果以 `docs/meta-narrative-audit-001-106.md` 为准。以下内容仅保留原写作、连续性、长度等审计记录，不再单独代表“全书全部维度通过”。**\n",
        ),
    ],
}


def main() -> int:
    total = 0
    for path, replacements in PATCHES.items():
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in replacements:
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"{path}: expected exactly 1 occurrence, found {count}")
            text = text.replace(old, new, 1)
            total += 1
        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"patched {path}")
    print(f"total documentation patches={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
