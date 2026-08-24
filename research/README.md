# 小说立项研究

> 分支：`research/seed-market-validation`
>
> **正文冻结。** 数据门槛完成并重新立项前，不继续正文、不写SEED V3试读，也不因为旧稿投入而默认必须救SEED。

## 计数规则

上一聊天窗口曾报告“候选100+ / 深读24 / 极深读8”，但逐本原始账本没有完整落入Git，窗口达到上下文上限后无法完整恢复。

因此旧数字全部只作 **historical / not counted**。当前只统计本轮重新打开来源、重新核验并写入仓库的样本。

当前权威逐本账本：`research/sample-ledger-v2.md`。旧`sample-ledger.md`保留为重建中期快照，不再作为当前总计数来源。

## 恢复创作前硬门槛

- 高可信原生元数据：≥50本；
- 深读：≥24本；
- 极深读：≥8本；
- 深读中弱表现 / 失败 / 停更对照：≥30%；
- 每本记录原生/首发平台、分发渠道、指标语义、连载状态、作品年龄/观察窗口、抓取日期和source confidence；
- 分发渠道可以用于发现和阅读，但不能单独用于判断原生表现；
- 新书不得因为短期低指标就贴“失败”。

## 当前严格进度

- **高可信原生元数据：≥35 / 50**
- **深读：24 / 24 ✅**
- **极深读：8 / 8 ✅**
- **深读弱/停更：8 / 24 = 33.3% ✅**

横向深读、极深读和弱样本比例三个门槛均已完成。**仍不恢复创作**：原生元数据50本尚未完成，且达到50后仍需要统一编码和反过拟合审计。

## 当前8本极深读

1. 《科技：为了上大学，上交可控核聚变》——书旗强；
2. 《重生1999：开启黑科技时代》——阅文长线强；
3. 《首富从AI浪潮开始》——起点现代AI强；
4. 《带着手机重生，目标科技教父》——番茄年代AI强；
5. 《重生九零年代，人工智能带我飞》——番茄年代AI弱；
6. 《重生：我体内带个台式机》——番茄成长计算能力强；
7. 《超级全能学生》（紫函）——番茄全能能力弱；
8. 《我靠打爆学霸兑换黑科技》——番茄反馈燃料长线强。

完整24本名单与状态见`sample-ledger-v2.md`。

## 极深读完成后的核心修正

### 1. SEED最值得保留的是“真实反馈成为成长燃料”

目前最强的结构参照不是“系统等级越来越高”，而是：

> **现实问题 → 外部真实反馈/错误 → 能力学习或成长 → 回到同一现实问题 → 更强结果 → 新反馈。**

《重生1999：开启黑科技时代》《重生2005，AI客服称霸电商》《我靠打爆学霸兑换黑科技》分别从长期成长、AI产品和系统燃料三个方向支持这一点。

### 2. 多能力不是原罪，关键是`application_target_coherence`

枪、雷达、声呐可以同时出现，只要它们都服务“这艘船和家人活着回来”。

SEED可以在同一项目里学会多个子能力，但这些能力必须先围绕同一个现实应用靶协同，而不是随机展开五条题材线。

### 3. 真正需要看的是`progress_topology`

极深读02把三个样本区分得更清楚：

- 《重生：我体内带个台式机》：**纵向累计**——255→597→高考→名校→大学→公司/产业；
- 《超级全能学生》：更像**横向模块巡演**——格斗、学习、篮球、彩票等连续展示“我还能做这个”；
- 《我靠打爆学霸兑换黑科技》：**反馈闭环**——现实竞争制造怨念资源，资源又帮助回到同一竞争，下一次现实反馈继续供能。

因此新增：

- `progress_topology`
- `cumulative_progress_legibility`
- `module_demo_trap`
- `scoreboard_saturation_speed`
- `progression_headroom`
- `resource_loop_visibility`

### 4. 修正对《超级全能学生》的旧判断

它并不是“书名承诺和正文不一致”。书名与简介本来就明确卖“全能”，学习、战斗、体育等都属于承诺内容。

真正值得研究的问题是：**一次次爽点是否能累加在同一条人生进度线上。**

它第一章的人类利益也不弱：父亲长时间跑出租攒学费、主角班级吊车尾、目标是考好大学改善家庭。弱表现不能简单归因于“没有现实计分板”。

这条修正用于防止研究模型为了迎合结果倒推原因。

### 5. 第一块计分板需要`progression_headroom`

如果“吊车尾→顶级学术奖励”在很少章节内就接近天花板，后续容易被迫横向换爽点。

SEED第一阶段更适合：

> 基线失败率/收入/排名 → 小幅改善 → 稀缺机会 → 第一真实客户/合同 → 可复制产品 → 更大的组织/市场问题。

每次都有proof，但不能第一轮就把同方向的成长空间打满。

### 6. `resource_loop_visibility`对SEED尤其重要

内部AI机制可以复杂，但读者看到的循环必须简单：

> **哪里失败 → 收到什么真实反馈 → SEED学会什么 → 哪个现实指标变好。**

如果这四步无法被读者轻松复述，机制很容易再次变成“AI能力本身就是剧情”。

### 7. AI知道不等于现实承认

`proof_burden`继续保留：能力发现问题后，现实仍需要证据、实验、部署、说服、交易、合规或组织执行。

《首富从AI浪潮开始》的核心优势之一就是没有把“AI知道”直接写成“全世界自动承认”。

### 8. 主角不能被AI吃空

继续保留`agency_share / protagonist_value_capture`：主角必须负责问题选择、数据采集、应用决策、证明、部署、交易和风险承担，而不是只把问题转给SEED。

### 9. 最终大兑现可以晚，但中间proof不能断

`intermediate_proof_density`继续成立。《带着手机重生，目标科技教父》直到第25章才出现明确第一单，但此前产品、网店、网站、流量等不断提供现实验证。

所以不再机械追求“前三章必须赚钱”。

### 10. 强外挂也可以成立，只要约束没有全部死亡

继续使用`constraint_portfolio`和`constraint_transfer`：一个能力可以清空制造成本或信息差，只要信誉、市场、时间、产能、证明、组织、债务等其他压力仍然存在，故事仍可以运转。

## 当前核心编码字段

基础字段：

- `scoreboard_latency`
- `ability_demo_latency`
- `conversion_latency`
- `witness_density`
- `earned_witness_ratio`
- `friction_survival`
- `objective_concentration`
- `promise_coherence`
- `earnedness`
- `credibility`
- `scarcity`
- `proof_burden`
- `reader_facing_demo_bandwidth`
- `stage_gate_closure`
- `causal_attribution_clarity`
- `human_stake_preload`
- `scoreboard_coupling`
- `reward_before_proof`
- `reward_proportionality`
- `payoff_scene_density`
- `observation_window`

当前追加字段：

- `constraint_portfolio`
- `constraint_transfer`
- `feedback_fuel_alignment`
- `technology_context_fit`
- `agency_share / protagonist_value_capture`
- `creation_agency`
- `reaction_spectacle_carry`
- `reaction_novelty_decay`
- `promise_surface_alignment`
- `application_target_coherence`
- `capital_before_product_validation`
- `agency_before_cheat`
- `intermediate_proof_density`
- `progress_topology`
- `cumulative_progress_legibility`
- `module_demo_trap`
- `scoreboard_saturation_speed`
- `progression_headroom`
- `resource_loop_visibility`

这些字段还不是最终100分模型。下一步要通过24本统一编码压缩掉高度相关/重复变量。

## 当前SEED候选闭环

如果最终保留SEED，目前最值得测试的是：

> **具体现实任务 → 主角做判断/选择 → 真实失败与数据/用户反馈 → SEED只学习解决当前失败所需的能力 → 回到同一现实指标复测 → 连续小proof → 主角负责应用选择、证明、部署、交易和风险 → 外界验证 → 新反馈成为下一轮燃料。**

必须避免：

- 机制论文型：解释学习过程吞掉现实剧情；
- AI外包型：主角只提问，SEED完成全部高价值劳动；
- 模块巡演型：这一章黑客、下一章投资、再下一章格斗；
- 第一计分板过早打满；
- 产品/能力未proof先给巨额资金、权威和渠道；
- 另一个外挂抢走SEED应完成的第一现实兑现；
- 用分发平台指标误判原生表现。

## 下一步

1. **高可信原生元数据35→50**：继续补七猫、纵横、刺猬猫、17K、书旗、塔读；17K字段不稳定时仍不凑数。
2. **统一编码24本**：用同一字段把成功、弱、普通/观察样本放进同一矩阵，重点寻找真正有区分度的变量。
3. **反过拟合审计**：优先研究《重生2005，AI客服称霸电商》《魔法冠冕改AI》等“结构像正确答案但没有大成”的样本。
4. **补市场表层变量**：标题/简介点击承诺、人物吸引力、叙事声音、题材拥挤度、推荐窗口。
5. 全部完成后才比较现代现实困境SEED、现代创业SEED、年代SEED、全民AI进化等候选。

## 研究文件

- `sample-ledger-v2.md`：当前权威逐本账本
- `round-2026-08-24-extreme-pair-02.md`：极深读6～8与进展拓扑
- `round-2026-08-24-extreme-pair-01.md`：年代AI成败极深配对
- `round-2026-08-24-rebuild-03.md`：深读20～24与现代AI/跨平台校正
- `round-2026-08-24-rebuild-02.md`：极深读1～2与前一轮重建
- `round-2026-08-24-rebuild-01.md`：首轮重建
- `round-2026-08-24-weak-pairs.md`：弱样本反例
- `platform-matrix-rebuild-01.md`：平台矩阵
- `next-handoff.md`：下一窗口执行入口

**现在仍不立项、不写正文。**