# 《末世列车求生：我能融合整座车站》

番茄小说持续更新项目。该目录只保存本书自己的正文、设定、大纲、连续性账本和平台进度，不与其他小说共享世界观或人物资料。

## 当前状态

- 平台：番茄小说
- Fanqie book_id：`7670480372831882302`
- 番茄作者后台已完成一次第1～70章全文导出，70/70均为 `author-editor` 原文
- 第58、59章已于2026-08-26按审计结果回修，待下一次导出校准新平台字数
- 第一卷《初生移动站》：第1～35章，已完成
- 第二卷《北境七站》：进行中
- 最新平台导出稿：第70章《炉坪今天第一次下班》
- 最新仓库新稿：第71章《想进旧港，先上秤》
- 下一章：第72章
- 当前主线：炉坪工务站阶段收束；轻型接驳编组通过旧港东联络桥称重检查，开始进入旧港现存交易/路线体系

## 重要：2026-08-26 平台/仓库漂移恢复

已确认番茄实际正文与仓库旧逐章正文**从第1章起就存在版本差异**。过去曾发生“聊天中完成重写 → 平台已替换 → 新版未同步回 GitHub”的情况。

因此：

1. 番茄 `author-editor` 全文导出是恢复旧正文的历史真源；
2. 已恢复的新逐章正文与新写章节重新作为续写事实源；
3. 尚未恢复的旧章节不得反向覆盖平台真实稿；
4. 每次新章完成后必须同步：章节正文、`chapters/index.md`、`docs/next-window-handoff.md`，必要时更新连续性/短期大纲。

同步工具：

`novels/endless-rail/scripts/sync-fanqie-export.py`

## 当前恢复进度

- 平台真实稿：第1～70章已拿到。
- 逐章正文已优先恢复第67～70章。
- 第71章已直接写入 `chapters/volume-02/chapter-071.md`。
- 其余历史章节继续按平台导出恢复；完整恢复前以 `docs/next-window-handoff.md` + 已恢复最新逐章正文为续写依据。

## 当前必读顺序

1. `novels/endless-rail/chapters/volume-02/chapter-069.md`
2. `novels/endless-rail/chapters/volume-02/chapter-070.md`
3. `novels/endless-rail/chapters/volume-02/chapter-071.md`
4. `novels/endless-rail/docs/next-window-handoff.md`
5. `novels/endless-rail/docs/writing-rules.md`
6. `novels/endless-rail/docs/long-term-outline.md`
7. `novels/endless-rail/docs/master-outline.md`
8. `shared/` 最新研究规则

## 目录

- `chapters/`：正文、章节索引、平台同步清单
- `docs/`：世界观、总纲、短期大纲、连续性账本、写作规则和续写交接
- `scripts/`：番茄全文同步与恢复工具

## 与通用规则的关系

仓库顶层 `shared/` 提供跨小说复用的结构、市场和去AI腔规则；如果通用规则与本书已经建立的连续性冲突，以本书**实际已发布正文**为准，不允许为了套模板破坏既有故事。
