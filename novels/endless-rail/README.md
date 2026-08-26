# 《末世列车求生：我能融合整座车站》

番茄小说持续更新项目。该目录只保存本书自己的正文、设定、大纲、连续性账本和平台进度，不与其他小说共享世界观或人物资料。

## 当前状态

- 平台：番茄小说
- Fanqie book_id：`7670480372831882302`
- 番茄作者后台已导出：第1～70章，70/70均为 `author-editor` 原文
- 平台已发布：第1～59章
- 待发布/定时稿：第60～70章
- 第一卷《初生移动站》：第1～35章，已完成
- 第二卷《北境七站》：进行中
- 最新稿：第70章《炉坪今天第一次下班》
- 下一章：第71章
- 当前主线：炉坪工务站阶段收束，获得通往旧港的真实工务维护廊线索

## 重要：2026-08-26 平台/仓库漂移恢复

已确认番茄实际正文与仓库旧逐章正文**从第1章起就存在版本差异**。过去曾发生“聊天中完成重写 → 平台已替换 → 新版未同步回 GitHub”的情况。

因此，在 `scripts/sync-fanqie-export.py` 将最新番茄全文导出完整同步进逐章文件以前：

1. `docs/next-window-handoff.md` 是当前剧情状态的第一权威交接文件；
2. 旧的 `chapters/` 正文、`chapters/index.md` 和旧连续性账本不得单独用于续写；
3. 不允许再拿仓库旧版覆盖平台已发布正文；
4. 同步完成后，仓库逐章正文重新成为后续写作事实源。

同步工具：

`novels/endless-rail/scripts/sync-fanqie-export.py`

它会校验 `source=author-editor`、重建逐章正文、章节索引和平台来源哈希清单。

## 当前必读顺序

1. `novels/endless-rail/docs/next-window-handoff.md`
2. 平台同步后的 `chapter-068.md`
3. `chapter-069.md`
4. `chapter-070.md`
5. `novels/endless-rail/docs/writing-rules.md`
6. `novels/endless-rail/docs/long-term-outline.md`
7. `novels/endless-rail/docs/master-outline.md`
8. `shared/` 最新研究规则

详细人物、能力、暖桥/沉泉/麦丘/炉坪连续性和第71章入口，以 `docs/next-window-handoff.md` 为准。

## 目录

- `chapters/`：正文、章节索引、平台同步清单
- `docs/`：世界观、总纲、短期大纲、连续性账本、写作规则和续写交接
- `scripts/`：番茄全文同步与恢复工具

## 与通用规则的关系

仓库顶层 `shared/` 提供跨小说复用的结构、市场和去AI腔规则；如果通用规则与本书已经建立的连续性冲突，以本书**实际已发布正文**为准，不允许为了套模板破坏既有故事。
