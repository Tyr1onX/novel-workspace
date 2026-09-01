# 《末世列车求生：我能融合整座车站》

番茄小说持续更新项目。本目录只保存本书正文、设定、大纲、连续性账本和平台同步状态；其他小说只共享 `shared/` 中的通用方法，不共享世界观与人物事实。

## 当前状态

- 平台：番茄小说
- Fanqie book_id：`7670480372831882302`
- 历史平台权威源：2026-08-26 13:34:55 番茄作者后台 `author-editor` 第1～70章完整导出
- 第1～70章：已按该导出恢复为逐章正文；第6、7、8、30章人物连续性小修已回填平台
- 第71～86章：恢复完成后的仓库新稿/修正版
- 第87～106章：完成逐章审计与全量连续性复核；详见 `docs/audit-087-106.md`
- 第107～116章：2026-09-01 按新 Narrative Pass 续写10章并完成全量门禁；详见 `docs/narrative-pass-audit-001-116-20260901.md`
- 第88～106章：2026-08-30 追加最新 Dialogue / Humanizer 审计；真实高风险段落已优先在未发布库存中整改，书级规则见 `style/HUMANIZER_FEEDBACK.md`
- 最新仓库正文：第116章《门锁能开了，电池还在掉温》
- 下一章：第117章
- 第一卷《初生移动站》：第1～35章，已完成
- 第二卷《北境七站》：第36～94章，已完成
- 第三卷《联轨商路》：第95章起，进行中

## 当前阶段

第87～88章已完成北岬 `N-3-4` 收束；第89～92章兑现燃料运输、空返、K-17道岔维护成本与备用绕行线；第93～94章通过真实任务跑通第一条稳定互助线路，第二卷结束。

第95～105章完成第三卷第一篇“标准停靠”的第一轮实体兑现：

- P-01模块化可调装卸桥；
- 50mm快接→40mm螺纹洁净水路转换件；
- LV-01 48V→24V有限低压转换箱；
- AC-01同电压专用接口线；
- 站点停靠卡、A/B/C装载等级；
- 维修交接摘要、跨站对象索引；
- 毛重/皮重/净重及称重来源字段；
- 上述字段接入归途站现有公开货单/库存页面。

这些只是当前七站真实任务验证过的有限工具和记录方式，不等于全区域统一接口、统一价格、成熟信用或保险制度。各固定站仍保留自己的设备、记录、拒绝权和路线权。

第106～116章推进第三卷第二篇“寒季供应”：真实取舍已经落到72h最低能源线、固定站分担、K-17低温暂停与≤6t西侧备用线实战。第116章进一步把低温故障反馈到归途站自身：货运门挡水片、P-01收纳防水罩/红色提醒带和低温工具位进入试用，电池舱外侧检修门/金属骨架低温下降最快，等待第117章根据夜间数据完成有限寒季运输组件。

## 路线硬状态

- 炉坪—旧港维护廊：双方确认 / 轻型人工通行；白03每次实际任务仍需炉坪登记。
- 归途站主体不能通过维护廊直接进入旧港。
- 北岬外仓线：实体往返确认 / **无归途站通行授权**；继续经北岬黄牌车 + 旧港中转。
- 三号收货无权替外仓线务发黄牌；旧港无权替其他站授权。
- 西侧绕行支线：受控轻型货运可用，当前总重≤6t，成本更高，只作为K-17异常时的应急替代，不是日常主路。

## 续写前必读

1. `chapters/volume-03/chapter-113.md`
2. `chapters/volume-03/chapter-114.md`
3. `chapters/volume-03/chapter-115.md`
4. `chapters/volume-03/chapter-116.md`
5. `docs/next-window-handoff.md`
6. `docs/continuity-update-107-116.md`
7. `docs/character-memory-update-107-116.md`
8. `docs/narrative-pass-audit-001-116-20260901.md`
9. `docs/writing-rules.md`
10. `docs/reading-payoff-rules.md`
11. `docs/short-term-outline.md`
12. `docs/development-blueprint-107-510.md`
13. `docs/capability-growth-ledger.md`
14. `docs/long-term-outline.md`
15. `docs/master-outline.md`
16. `style/HUMANIZER_FEEDBACK.md`
17. `shared/NARRATIVE_PASS_RULES.md`
18. `shared/RULES.md`
19. `shared/DIALOGUE_RULES.md`
20. `shared/HUMANIZER_RULES.md`
21. `shared/PROSE_RULES.md`
22. `shared/META_NARRATIVE_RULES.md`

后续任何新章、重写或平台同步前，除事实连续性审计外，必须执行完整语言门禁：

`Narrative Pass → Dialogue → Humanizer → Prose → Meta → Continuity → 人工复核`

自动 WARN 只负责定位，不能为了清零告警机械改写真实货单、接口卡、系统框、型号、尺寸和必要安全检查。

## 权威顺序

历史已发布正文发生争议时：最近一次明确验证的平台导出优先。第71章以后以仓库当前逐章正文为事实源；第107章以后新增事实以当前正文、`continuity-update-107-116.md` 与最新审计文档为准。大纲和聊天记录不能反向覆盖已发生正文。
