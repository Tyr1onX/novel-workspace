# Novel Workspace Agent Instructions

本文件对在本仓库内工作的 AI / Agent 生效。

## 1. 正文任务必须先读规则，禁止直接开写

凡任务涉及以下任一情况：

- 新写小说章节；
- 续写；
- 大幅改稿；
- 润色；
- 去 AI 味；
- 对白优化；
- 正文审计；

开始动正文前至少读取：

1. `shared/RULES.md`
2. `shared/DIALOGUE_RULES.md`
3. `shared/HUMANIZER_RULES.md`
4. `shared/PROSE_RULES.md`
5. `shared/META_NARRATIVE_RULES.md`
6. 当前小说自己的 README / design / continuity / style 文件
7. 当前小说若存在：
   - `style/DIALOGUE_VOICES.md`
   - `style/VOICE_SAMPLES.md`
   - `style/HUMANIZER_FEEDBACK.md`
8. 与当前场景直接连续的上一章正文

禁止只根据用户一句“继续写”或章节卡直接生成正文。

## 2. 固定正文流水线

正文默认必须走：

```text
Story / Continuity
      ↓
First Draft
      ↓
Dialogue Pass
      ↓
dialogue_guard.py
      ↓
Humanizer Pass
      ↓
humanizer_guard.py
      ↓
Prose Pass
      ↓
prose_guard.py
      ↓
meta_narrative_guard.py
      ↓
Continuity / Numbers / Final Read
```

没有对白的章节可以跳过 Dialogue Pass，其余不能因为“看起来没问题”跳过。

## 3. 运行检查

至少按适用情况运行：

```bash
python shared/tools/dialogue_guard.py <chapter.md>
python shared/tools/humanizer_guard.py <chapter.md>
python shared/tools/prose_guard.py <chapter.md>
python shared/tools/meta_narrative_guard.py <chapter.md>
```

工具只定位风险，不自动决定改法。不能通过批量替词、机械碎句、强行删标点来追求 WARN=0。

## 4. 去 AI 味不是一次性 prompt

本仓库采用长期 Humanizer 机制：

- 禁止层：`shared/HUMANIZER_RULES.md` 等共享规则；
- 语气层：单本小说的 `STYLE_DNA`、`DIALOGUE_VOICES`、`VOICE_SAMPLES`；
- 审核层：guards + 人工回读；
- 反馈闭环：作者/读者反馈写入 `style/HUMANIZER_FEEDBACK.md`，稳定结论再回写规则。

外部 humanizer 规则不能覆盖本书已经验证的人物声音和作者人工选择。

## 5. 修订前锁事实

大改前先确认并保护：

- 金额、步数、里程、距离、日期、时间、等级、收益倍率；
- 人名、地点、学校、公司、产品等专名；
- 谁知道什么、谁见过谁、物品在哪、关系进展；
- 已建立的角色立场；
- 系统通知、短信等承担事实锚点的内容。

去 AI 味不能制造连续性错误。

## 6. 人工/读者反馈必须沉淀

当用户明确指出某种写作问题，尤其：

- AI 味；
- 对话硬；
- 角色说话像一个人；
- 解释太多；
- 金句太多；
- 三段式/对举太重；
- 节奏像模板；

不能只修当前一句。

必须判断它是：

- 单章问题；
- 单本小说稳定问题；
- 跨项目通用问题。

单本问题写入对应 `style/HUMANIZER_FEEDBACK.md`；跨项目重复验证后才升级到 `shared/`。

## 7. 语气样本优先于形容词

存在 `VOICE_SAMPLES.md` 时，必须先读样本，再写或改。

学习的是：

- 句长变化；
- 注意力落点；
- 信息分配；
- 人物如何被现场打断；
- 哪些地方作者选择不解释。

禁止复刻样本原句、口头禅和固定句式。

## 8. 禁止“规则腔”

不要为了像真人而：

- 故意加“嗯、呃、其实、就是”；
- 故意错别字；
- 每三句插一个动作；
- 每个问句都答非所问；
- 把所有排比、破折号、比喻清零；
- 强行制造不确定和矛盾；
- 凭空给角色补经历和立场。

规则服务故事，不反过来让故事服务规则。

## 9. 提交正文前

必须确认：

- 情节和连续性未被润色破坏；
- 重要数字一致；
- 主要人物声音可区分；
- 没有明显 AI 解释尾巴、假深刻、强行金句；
- 本章存在只属于本场景的具体材料；
- 已按规则人工复核 guard 命中。

如果做不到，正文仍是草稿，不得把它当作后续续写基准。
