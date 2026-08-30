# Shared

这里存放所有小说项目共同复用的方法，不存任何单本小说的正文或专属设定。

## 当前内容

- `RULES.md`：从现有市场深读、强弱对照和结构编码中压缩出的通用创作规则。
- `DIALOGUE_RULES.md`：人物对白自然度、交流结构、角色声音与配角功能化的共享规则。
- `HUMANIZER_RULES.md`：跨小说通用的 AI 写作痕迹、保护清单、正向 humanize 与审核规则。
- `HUMANIZER_EVOLUTION.md`：把作者校稿、读者反馈和改前→改后差异回写成长期资产的自我更新协议。
- `PROSE_RULES.md`：所有小说正文共享的语言与叙述姿势硬闸门。
- `META_NARRATIVE_RULES.md`：元叙事/作者替读者下结论等风险规则。
- `tools/dialogue_guard.py`：对白结构风险定位工具，只报警，不自动改稿。
- `tools/humanizer_guard.py`：通用 AI 写作模式与节奏风险定位工具，只报警，不自动改稿。
- `tools/prose_guard.py`：正文叙述高风险模式定位工具，只报警，不自动改稿。
- `tools/meta_narrative_guard.py`：元叙事风险扫描。
- `evals/HUMANIZER_BENCHMARK.md`：Humanizer 规则的 Should Fix / Should Not Fix / 事实保真回归用例。
- `research/humanizer-external-sources-v1.md`：RAR 文章与 humanizer / Humanizer-zh / speak-human-tw 三个公开项目的详细吸收审计。
- `research/`：其他研究证据、样本账本、Click / Activation / Retention / Scale 模型、平台分层、反过拟合记录。

## 正文默认工作流

任何 `novels/*/` 下的新正文、新写续章或大幅改稿默认执行：

1. 读取当前小说自己的 README / design / style / continuity；
2. 读取 `RULES.md`；
3. 读取 `DIALOGUE_RULES.md`；
4. 读取 `HUMANIZER_RULES.md` 与 `HUMANIZER_EVOLUTION.md`；
5. 读取 `PROSE_RULES.md` 与 `META_NARRATIVE_RULES.md`；
6. 如果当前小说存在 `DIALOGUE_VOICES.md`、`VOICE_SAMPLES.md`、`HUMANIZER_FEEDBACK.md`，必须一并读取；
7. 写第一稿，优先人物目标、动作、冲突和结果，不边写边机械躲关键词；
8. 有两人及以上对白时做 Dialogue Pass，并运行 `dialogue_guard.py`；
9. 做 Humanizer Pass，并运行 `humanizer_guard.py`；
10. 做 Prose Pass，并运行 `prose_guard.py` / `meta_narrative_guard.py`；
11. 人工检查全部高风险命中；
12. 做数字、连续性、人物声音和最终朗读复核；
13. 通过后才把这一章当作后续续写基准。

推荐命令：

```bash
python shared/tools/dialogue_guard.py <chapter.md>
python shared/tools/humanizer_guard.py <chapter.md>
python shared/tools/prose_guard.py <chapter.md>
python shared/tools/meta_narrative_guard.py <chapter.md>
```

扫描结果不能替代人工判断，也禁止为了降低命中数机械碎句、批量换同义词或清除作品本来成立的文学表达。

## 自我更新工作流

只要作者亲手修改、明确选择版本，或读者提供清晰的语言反馈，就不能“改完正文就结束”。

必须按 `HUMANIZER_EVOLUTION.md`：

```text
保存原反馈
↓
找正文证据
↓
比较改前→改后
↓
解释为什么作者更喜欢新版本
↓
形成候选规则
↓
后续章节和反例验证
↓
稳定后升级到单本 style 或 shared
```

单本小说应把原始记录放在 `style/HUMANIZER_FEEDBACK.md`；作者认可的正向语气样本放在 `style/VOICE_SAMPLES.md`。

## 升级规则

只有满足以下任一条件，结论才允许进入 shared：

1. 有多个独立强样本与反例支持；
2. 在不同平台或不同题材中重复出现；
3. 在我们自己的多个小说项目中反复验证；
4. 有多个外部独立来源支持，且本仓库正文也验证；
5. 能解释旧规则解释不了的反例，并且不会只是为单本书量身定制。

任何共享规则都必须同时考虑误杀边界。规则增加后如果出现新的“规则腔”，应降级、修改或撤销，而不是继续叠规则。

单本小说的局部技巧、角色设定、机制边界、风格例外和运营判断留在对应 `novels/<project>/` 内。
