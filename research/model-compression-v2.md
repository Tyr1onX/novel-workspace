# 模型压缩 V2

> 日期：2026-08-24
> 前置：`unified-coding-v2.md`、`click-layer-v1.md`、`platform-stratification-v1.md`。
> 正文继续冻结。

## 目标

24本编码已经证明多个字段高度共线。最终不能把相近现象重复加分，也不再追求伪精确100分表。本轮把模型压成4层 + 1个SEED专属项。

## 1. Click Layer

### C1 `surface_causal_compression`

合并`surface_conflict_compression`、`fantasy_specificity`和部分概念负载。

核心问题：读者能否很快复述“谁遇到什么问题 → 有什么异常能力/资源 → 第一次具体利益是什么”。

### C2 `surface_explanation_load`（风险）

吸收`premise_explanation_tax`和不可串联的`premise_concept_load`。

新增修正`concept_chainability`：不是简单数概念，而是多个概念能否串在同一条因果链上。

### C3 `claim_grounding`

合并`event_specificity`与`authorial_hype_ratio`。

允许夸张，但强结论前应先有具体事件骨架。问题不是能不能写“震惊/无敌”，而是有没有事实让读者知道下一步究竟发生什么。

### C4 `surface_story_alignment`

保留表层承诺与前20章真实主线的对齐度。

## 2. Activation Layer

### A1 `human_stake_confirmation`

前三章内，能力成功究竟改变主角或家人的什么。它是卫生项，不再作为高权重成功预测。

### A2 `first_real_world_proof`

不再机械统计“第几章赚钱”，而看核心异常是否尽快改变一个现实可验证结果。

### A3 `agency_signal`

前三章是否已经看到主角本人做判断、选择并承担后果，而不是只按按钮。

## 3. Retention Layer

### R1 `progress_architecture`

合并原来的`progress_focus / progress_legibility / progress_headroom`。

它统一吸收：应用靶集中、目标连续拆解、累计进度、阶段结算、模块巡演风险和计分板过早饱和风险。

只回答一个问题：连续爽点能否组成一条聚焦、可累计、阶段结算后仍有下一格的进展。

### R2 `causal_ownership`

核心成果到底属于谁，主角本人是否拥有足够价值占比。

### R3 `friction_survival`

合并proof burden、constraint survival和constraint transfer。

外挂知道或能做以后，现实证明、钱、时间、市场、组织、信誉、产能、合规等摩擦是否仍然存活。允许强外挂消灭部分约束，只要压力能转移到新的真实约束。

## 4. SEED专属项

### `feedback_loop_fit`

只在候选明确卖“从真实反馈成长”时计算，普通作品标N/A，不扣分。

核心问题：真实反馈是否既是剧情结果，又成为下一轮能力改进的燃料；反馈 → 学习 → 复测的循环是否对读者清楚可见。

当前正参照仍是《重生1999》《我靠打爆学霸》《AI客服》。

## 5. Scale Layer

### `long_tail_engine`

底层机制能否从小问题扩大到团队、产品、公司、产业，而不是只能重复第一招。

### `distribution_confidence`

综合原生/分发身份、recommendation state、exposure observability、observation window和指标语义。它不是质量分，而是我们对市场结论有多大把握。

### `author_supply`

更新、停更、完结与供给连续性单独处理。《重生手搓ChatGPT》说明停更不能全部解释成Click或Retention失败。

## 6. 旧字段处理

以下降级为解释证据，不再单独占评分槽：

- human_stake_preload
- promise_surface_alignment
- intermediate_proof_density
- witness_density
- earned_witness_ratio
- scoreboard_coupling
- reaction_spectacle_carry
- reaction_novelty_decay
- reward_proportionality
- technology_context_fit
- reader_facing_demo_bandwidth

以下保留为风险诊断标签，不单独计总分：

- reward_before_proof
- capital_before_product_validation
- module_demo_trap
- scoreboard_saturation_speed
- retrospective_effort_credit

## 7. 立项阶段的输出格式

以后每个候选直接展示分层矩阵，不先加成一个总数：

- Click：C1 / C2 / C3 / C4
- Activation：A1 / A2 / A3
- Retention：R1 / R2 / R3
- SEED专属：feedback_loop_fit 或 N/A
- Scale：long_tail_engine / distribution confidence / author supply假设
- Evidence：high / medium / low

如果最终必须加权排名，再做权重敏感性测试：如果Click权重从20%改40%就导致排名大幅翻转，说明结论不稳，不应伪装成“87分胜过84分”。

## 8. 目前真正稳定的通用规律

1. 入口因果要短：不是设定少，而是第一利益容易复述；
2. 前三章要有现实proof与主角agency；
3. 连续爽点必须组成一条进展，而不是功能巡演；
4. 主角要拥有核心成果的因果所有权；
5. 能力再强，现实摩擦不能全部死亡；
6. 市场数字必须经过平台、推荐状态和作者供给校正；
7. 对SEED额外要求：真实反馈 → 学习 → 复测的循环必须可见且与主线同源。

## 下一步

进入候选机制比较：现代强现实困境+SEED、现代职场/创业+SEED、年代+SEED、全民AI环境+独特反馈进化、原版大学生+SEED，并加入至少一个非SEED控制。只做机制和外壳比较，不写正文、不定书名。前三名再定向补样本。
