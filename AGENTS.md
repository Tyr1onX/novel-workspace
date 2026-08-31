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
2. `shared/STORY_ARCHITECTURE_RULES.md`
3. `shared/NARRATIVE_PASS_RULES.md`
4. `shared/DIALOGUE_RULES.md`
5. `shared/DIALOGUE_APPRENTICESHIP.md`
6. `shared/HUMANIZER_RULES.md`
7. `shared/HUMANIZER_EVOLUTION.md`
8. `shared/PROSE_RULES.md`
9. `shared/META_NARRATIVE_RULES.md`
10. 当前小说自己的 README / design / continuity / style 文件
11. 当前小说若存在：
   - `style/DIALOGUE_VOICES.md`
   - `style/VOICE_SAMPLES.md`
   - `style/HUMANIZER_FEEDBACK.md`
12. 与当前场景直接连续的上一章正文

禁止只根据用户一句“继续写”或章节卡直接生成正文。

如果作者或读者已经明确说过“对白怪 / 对话硬 / 像 AI / 像排练”，必须按 `DIALOGUE_APPRENTICESHIP.md` 进入 `REBUILD`，不能在旧句上逐句润色。

## 2. 固定正文流水线

正文默认必须走：

```text
Research / Platform Evidence
      ↓
Commercial Chapter Goal
      ↓
Story / Continuity / Chapter Card
      ↓
Architecture Lite
      ↓
Dialogue Scene Card（有对白时）
      ↓
First Draft / REBUILD
      ↓
Payoff / Logic / Continuity Audit
      ↓
Discourse / QUD Pass
      ↓
narrative_guard.py
      ↓
Dialogue Pass + Read-Aloud
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
Cold Read（高风险对白强制）
      ↓
Continuity / Numbers / Final Read
```

`Architecture Lite` 与 `Discourse / QUD Pass` 的定义以 `shared/NARRATIVE_PASS_RULES.md` 为准。

没有对白的章节可以跳过 Dialogue Scene Card / Dialogue Pass，其余不能因为“看起来没问题”跳过。

开篇前三章、首次人物登场、关系转折、以及作者/读者已经投诉过的同类对白，必须执行 `DIALOGUE_APPRENTICESHIP.md` 的三版法与 Cold Read。

## 3. 运行检查

默认优先使用统一入口，避免漏掉某一层：

```bash
python shared/tools/novel_gate.py <chapter.md>
```

批量章节也可以一次传入：

```bash
python shared/tools/novel_gate.py chapter-041.md chapter-042.md chapter-043.md
```

`novel_gate.py` 会依次调用：

```text
narrative_guard.py
dialogue_guard.py
humanizer_guard.py
prose_guard.py
meta_narrative_guard.py
```

需要单独定位时才分别运行：

```bash
python shared/tools/narrative_guard.py <chapter.md>
python shared/tools/dialogue_guard.py <chapter.md>
python shared/tools/humanizer_guard.py <chapter.md>
python shared/tools/prose_guard.py <chapter.md>
python shared/tools/meta_narrative_guard.py <chapter.md>
```

`narrative_guard.py` V1 是 advisory review：身体化情绪、主题收束、因果连接词、主题化对白等命中只负责提醒人工复核，不因命中本身阻塞发布。缺文件/读文件失败仍会报错。

所有工具都只定位风险，不自动决定改法。不能通过批量替词、机械碎句、强行删标点、随机插入生活细节或故意打乱因果来追求 WARN=0。

**WARN=0 / Gate PASS 不是正文合格证。** 如果 QUD / Cold Read 仍然显示人物和事件像按作者安排轮流完成任务，必须回到结构层或 REBUILD。

## 4. 去 AI 味不是一次性 prompt，也不是只改表面词句

本仓库采用长期 Humanizer + Narrative 机制：

- 架构诊断层：`shared/STORY_ARCHITECTURE_RULES.md` + `shared/NARRATIVE_PASS_RULES.md`；
- 禁止层：`shared/HUMANIZER_RULES.md` 等共享规则；
- 对白训练层：`shared/DIALOGUE_APPRENTICESHIP.md`；
- 语气层：单本小说的 `STYLE_DNA`、`DIALOGUE_VOICES`、`VOICE_SAMPLES`；
- 审核层：guards + QUD + 人工回读 + Cold Read；
- 演化层：`shared/HUMANIZER_EVOLUTION.md`；
- 反馈闭环：作者/读者反馈写入 `style/HUMANIZER_FEEDBACK.md`，稳定结论再回写规则。

修稿顺序默认是：**架构 / 篇章推进 → 对白目的 → Humanizer / Prose 表面层**。如果结构本身过度整齐，禁止只靠换词、碎句和删“AI 高频词”伪装修复。

外部 humanizer / dialogue / narrative 项目只用于学习可迁移技法，不能覆盖本书已经验证的人物声音和作者人工选择，也不能复制某个作者或作品的固定句子、口癖和签名风格。

## 5. Narrative Pass 的强制最小集

每章至少完成以下检查：

- 章节卡有没有预先要求“总结主题/悟出道理”；
- 情绪是否被预设成连续身体反应；
- 因果是否形成“问题→正确分析→执行→结算→总结”的无摩擦链；
- 核心信息是否全部在场景开始前讲完；
- 新人物/重登场人物是否说明书式介绍；
- 至少一个主要场景写出隐含 QUD，并检查段落是否真的推进/改变它；
- 关键对白逐句问“这个人为什么现在必须说这句话？”；
- 每章只选择最需要的 3–5 个 human-leaning 调整，不机械执行全部技巧。

允许普通清楚的因果、普通句子和明确结算。禁止为了通过 Narrative Pass 强行倒叙、制造答非所问、加入无用支线或故意写乱。

## 6. 修订前锁事实

大改前先确认并保护：

- 金额、步数、里程、距离、日期、时间、等级、收益倍率；
- 人名、地点、学校、公司、产品等专名；
- 谁知道什么、谁见过谁、物品在哪、关系进展；
- 已建立的角色立场；
- 系统通知、短信等承担事实锚点的内容。

去 AI 味不能制造连续性错误。

## 7. 人工/读者反馈必须沉淀

当用户明确指出某种写作问题，尤其：

- AI 味；
- 对话硬；
- 读着怪 / 像排练；
- 角色说话像一个人；
- 解释太多；
- 金句太多；
- 三段式/对举太重；
- 节奏像模板；
- 情绪全靠胸口、呼吸、指尖等身体反应；
- 每章都像“发现问题—解决问题—总结”；

不能只修当前一句。

必须判断它是：

- 单章问题；
- 单本小说稳定问题；
- 跨项目通用问题。

单本问题写入对应 `style/HUMANIZER_FEEDBACK.md`；跨项目重复验证后才升级到 `shared/`。

如果一次“大规模去 AI 重写”已经通过自动审计，但作者再次明确说“还是怪”，必须把这次重写判定为**失败样本**，不能继续拿它训练后文，也不能把“已经发布”当作质量证明。

## 8. 人工校稿后强制执行 Diff Learning

只要作者发生了以下任一行为：

- 亲手改正文；
- 明确指出某个具体改法更好；
- 对两个版本作出选择；
- 明确说“以后不要这样写 / 以后就按这种感觉”；

Agent 在完成正文修改后，必须继续执行 `shared/HUMANIZER_EVOLUTION.md` 的 Diff Learning：

1. 比较改前与改后；
2. 提炼具体差异，禁止只写“更自然”；
3. 判断是 `LOCAL / CHARACTER / BOOK / SHARED_CANDIDATE`；
4. 写入 `style/HUMANIZER_FEEDBACK.md` 或对应 style 文件；
5. 只有满足升级阈值才把候选规则升级；
6. 必要时更新 `VOICE_SAMPLES.md` 的状态。

**不能改完正文就结束。校稿差异本身也是交付物的一部分。**

## 9. 语气样本优先于形容词

存在 `VOICE_SAMPLES.md` 时，必须先读样本，再写或改。

学习的是：

- 句长变化；
- 注意力落点；
- 信息分配；
- 人物如何被现场打断；
- 哪些地方作者选择不解释；
- 人物在压力下会怎样保护自己、绕开什么、说到几分。

禁止复刻样本原句、口头禅和固定句式。

未经作者确认的 AI 草稿只能作为 `CANDIDATE`，不能自动升为 `LOCKED`。作者已经明确说“读着怪”的版本必须从正向样本中移除，作为失败样本保留。

## 10. 禁止“规则腔”与去 AI 过度矫正

不要为了像真人而：

- 故意加“嗯、呃、其实、就是”；
- 故意错别字；
- 每三句插一个动作；
- 每个问句都答非所问；
- 把所有排比、破折号、比喻清零；
- 强行制造不确定和矛盾；
- 凭空给角色补经历和立场；
- 把“潜台词”理解成人人都阴阳怪气；
- 把“口语化”理解成所有人都只说极短句；
- 为了非线性每章都倒叙；
- 为了“生活感”给每章强塞无关支线；
- 为了避免身体反应把所有情绪都改成直陈；
- 为了开放性让每章都不结算。

规则服务故事，不反过来让故事服务规则。

## 11. 周期性自更新

每累计 5–10 个新章节：

1. 批量运行 `novel_gate.py`；
2. 做一次 Full Narrative Review：检查 QUD、因果模板、reveal 位置、情绪表达手段、配角工具化；
3. 检查跨章重复问句、重复口癖和角色固定功能；
4. 回看最近章节作者修改记录；
5. 更新 `HUMANIZER_FEEDBACK.md` 中候选规则的状态；
6. 检查 `VOICE_SAMPLES.md` 是否仍代表当前风格；
7. 抽至少 2 场对白做无修改说明的 Cold Read。

每个大篇章 / 卷额外做一次 Architecture Review：人物网络、支线工具化、因果单链、伏笔回收是否过于整齐，以及核心幻想和生活纹理是否仍然平衡。

每 30–50 章再做一次规则瘦身，检查是否因规则过多形成新的统一“规则腔”。

## 12. 提交与发布正文前

必须确认：

- 情节和连续性未被润色破坏；
- 重要数字一致；
- 主要人物声音可区分；
- 至少一个主要场景通过 QUD 人工检查；
- 关键对白能回答“为什么这个人现在必须说这句话”；
- 情绪没有被单一身体反应模板垄断；
- 没有明显 AI 解释尾巴、假深刻、强行金句；
- 本章存在只属于本场景的具体材料；
- 已按规则人工复核 guard 命中；
- 高风险对白已经通过三版法 / Cold Read；
- 如果本轮产生新的人工偏好/读者反馈，已经完成反馈回写。

收到明确对白负反馈后的整批重写，**不得只凭自动 guard 通过就直接发布**。开篇 1–3 章仍有排练感时，整批保持草稿状态。

如果做不到，正文仍是草稿，不得把它当作后续续写基准。
