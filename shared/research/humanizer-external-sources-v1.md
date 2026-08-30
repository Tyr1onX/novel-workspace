# Humanizer 外部来源审计 V1

> 目的：记录本仓库长期 Humanizer 体系吸收了哪些公开项目/文章、具体吸收什么、哪些内容不直接照搬。
> 这不是规则正文；真正执行以 `shared/HUMANIZER_RULES.md`、`shared/HUMANIZER_EVOLUTION.md`、`shared/DIALOGUE_RULES.md` 为准。

## 1. RAR：去 AI 味怎麼做才有效？別抄 Prompt，建一套會自我更新的寫作 Skill

URL：`https://rar.design/posts/de-ai-flavor-writing-skill-guide`

### 核心结论

文章把长期去 AI 味机制收敛成三层：

1. 禁止层：禁止句、标点、文体底线；
2. 语气层：3–5 篇真实样本、节奏和开场习惯；
3. 审核层：AI 按自己的规则先扫一遍，再交人工。

更重要的是文章第四章的自我更新闭环：

```text
禁止层
↓
AI 参考语气样本写草稿
↓
人工校稿
↓
AI 分析“这轮人工改了什么”
↓
把结论回写 skill
↓
AI 终审
↓
下一篇从更新后的 skill 开始
```

文章明确指出：真正有价值的不是下载来的禁止句，而是**把“AI 以为对、作者觉得不对”的差异持续累积成自己的规则**。

### 本仓库吸收

- 新增 `HUMANIZER_EVOLUTION.md`；
- 作者/读者反馈必须写入单本小说 `HUMANIZER_FEEDBACK.md`；
- 人工校稿后强制执行 Diff Learning；
- 新规则分 `OBSERVE → BOOK → SHARED`，避免一次修改直接污染全仓；
- 新增 `VOICE_SAMPLES.md` 机制，且未经作者认可的 AI 样本不能锁定；
- 每 10 章小复盘，每 30–50 章大复盘；
- 规则必须同时维护反例，防止形成“规则腔”。

### 不直接照搬

文章主要面向文章/内容写作。小说还必须额外解决：

- 人物声音；
- 完美接球式对白；
- 配角功能化；
- 数字/设定连续性；
- 长篇跨章复发。

这些由本仓库自己的 `DIALOGUE_RULES.md`、continuity 和小说 style 层补足。

---

## 2. `blader/humanizer`

仓库：`https://github.com/blader/humanizer`

许可证：MIT。

审计版本：SKILL.md metadata `2.11.2`。

### 主要价值

该项目不是“敏感词替换器”，而是系统列出 AI 写作模式与误杀边界。

本仓库重点吸收：

- 夸大意义/遗产；
- 模糊权威与虚假来源；
- 宣传性语言；
- `Not X but Y`；
- 强行三项；
- 同义换名循环；
- 重复句首；
- 假范围；
- 被动/缺主语；
- 破折号高密度；
- chatbot 残留；
- filler / hedge；
- 假“更深层真相”；
- 预告下一点；
- dramatic fragments；
- formulaic sayings；
- fake-candid openings；
- 回答没人提出的反对意见；
- 构造假选项再否定。

该项目最新版还强调：

- **作者样本优先于通用规则**；
- 具体、奇怪、混合情绪、真实旁逸斜出应被保护；
- 单个模式不能证明 AI，要看多个模式叠加；
- 去 AI 味时不能新增事实；
- 如果结构有问题，应整段重写，不要逐词打补丁。

### 小说适配

- “不得新增事实”在小说里改成“不得新增已经不受授权的连续性事实”；创作新章本身当然允许发明剧情细节；
- 破折号不采用全局零容忍，只控制无必要密度；
- 标题大小写、英文连字符等与中文网文无关的模式不作为主要规则；
- 对白结构仍需由本仓库独立处理。

---

## 3. `op7418/Humanizer-zh`

仓库：`https://github.com/op7418/Humanizer-zh`

许可证：MIT。

### 主要价值

该项目是 `blader/humanizer` 的简体中文适配，并参考 `hardikpandya/stop-slop`。

本仓库重点吸收其中文化后的五个检查方向：

- 直接性；
- 节奏；
- 信任读者；
- 真实性；
- 精炼度。

同时吸收：

- 删除填充短语；
- 打破公式结构；
- 变化句长；
- 不要把每个意思手把手解释完；
- “如果一句话听起来像可引用的金句，检查是否应该重写”；
- 连续相同句长、段落固定短句收尾、三项并列等快速扫描项。

### 小说适配

Humanizer-zh 主要仍面向文章/博客，因此只作为通用层，不直接承担人物对白自然度与长篇连续性。

---

## 4. `Raymondhou0917/speak-human-tw`

仓库：`https://github.com/Raymondhou0917/speak-human-tw`

许可证：MIT。

审计版本：SKILL.md `1.4.0`。

### 主要价值

相较前两个项目，它把长期治理做得更完整：

- 38 种 AI 痕迹；
- `references/patterns.md`；
- `references/humanize.md`；
- `references/protected-list.md`；
- `evals/benchmark.md`；
- 版本化结果和误杀率；
- 自动化/交互模式；
- 明确的“人味是作者的，不是编辑器的”边界。

其 `humanize.md` 的正向目标尤其重要：

- 对事实做出真实反应；
- 句长变化；
- 信息密度允许不平均；
- 允许矛盾；
- 允许立场随时间改变；
- 允许不收尾；
- 允许适度不完美；
- 但禁止“表演口语”“表演不确定”“替作者编经历”。

`protected-list.md` 强调改写前先锁定数字、专名、原话、承诺等不应漂移的内容；这对本仓库数字机制小说和长篇连续性非常有价值。

`evals/results-v1.4.0.md` 还验证了一个关键治理原则：

- Should Fix 要能抓；
- Should Not Fix 误杀率要守；
- 事实/保护清单漂移必须为 0；
- “人味”本身不适合硬打分，否则会形成另一套公式。

### 小说适配

不吸收：

- 台湾地区用语替换；
- 繁体标点本地化；
- 对外文章修改必须先逐条向用户确认的交互规定。

吸收：

- 保护清单；
- 误杀边界；
- 正向 humanize；
- benchmark / regression 思路；
- “不要编造人味”；
- 规则治理与版本化。

---

## 5. 三个仓库之间的关系

不是“三选一”。

本仓库采用：

```text
blader/humanizer
  → 英文/通用模式与误杀边界

op7418/Humanizer-zh
  → 简体中文表达层适配

speak-human-tw
  → 中文正向 humanize + 保护清单 + eval/治理

RAR 文章
  → 三层结构 + 自我更新回路

novel-workspace 自己
  → 小说对白、人物声音、连续性、长篇反馈学习
```

现成项目是起点，不能成为终点。

---

## 6. 当前落地文件

- `AGENTS.md`
- `shared/HUMANIZER_RULES.md`
- `shared/HUMANIZER_EVOLUTION.md`
- `shared/DIALOGUE_RULES.md`
- `shared/PROSE_RULES.md`
- `shared/META_NARRATIVE_RULES.md`
- `shared/tools/humanizer_guard.py`
- `shared/tools/dialogue_guard.py`
- 单本 `style/HUMANIZER_FEEDBACK.md`
- 单本 `style/DIALOGUE_VOICES.md`
- 单本 `style/VOICE_SAMPLES.md`（逐步建立）

后续每一次作者人工校稿都要继续为这些文件提供训练数据。
