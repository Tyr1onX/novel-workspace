# Novel Workspace

长期小说创作与研究工作区。

这个仓库不是某一本小说的专属仓库，而是统一管理不同平台、不同题材、彼此独立的小说项目。

## 结构

- `shared/`：跨小说复用的研究结论、写作规则与市场方法。
- `novels/`：每一本小说独立存放正文、设定、大纲、章节卡和平台状态。
- `AGENTS.md`：AI / Agent 在本仓库写正文、改稿、去 AI 味时必须遵守的入口规则。

## 当前小说

### `novels/endless-rail/`

《末世列车求生：我能融合整座车站》

- 平台：番茄小说
- 状态：持续更新
- 当前仓库正文：第1～86章；第66、86章为整改后的修正版，等待独立审计后再同步平台。

### `novels/walk-to-earn/`

《今天走了两万步，到账八百》

- 平台：番茄小说
- 状态：DRAFTING
- 核心：有效步行可以换成真钱；开局 0.04 元/步，累计里程推动单步价值成长。
- 当前正在执行第1～40章 Dialogue + Humanizer 全量整改，整改分支未完成前不得把旧版对白当作新章模板。

### `novels/second-pass/`

《开局小厂要倒闭，我让失败变成黑科技》

- 平台：七猫签约评估失败
- 状态：REJECTED / FROZEN
- 只保留为失败样本和研究材料，不继续作为当前新书。

### `novels/third-pass/`

《你最好第一次就杀死我》

- 状态：ABANDONED / ARCHIVED
- 核心标题与设定未通过作者自身点击测试，禁止继续续写。
- 原设计和第一章保留用于审计失败模式。

## 使用原则

1. 新小说一律在 `novels/<project>/` 下建立独立目录。
2. 不同小说的世界观、人物、正文、连续性账本和平台数据不得互相继承。
3. 只有经过多样本研究或多个项目反复验证的结论，才进入 `shared/`。
4. 某一本小说为了题材需要违反通用规则时，在该小说内部记录例外，不反向修改通用规则。
5. 市场数据必须区分平台、推荐状态、曝光可见性和作者供给，不能直接跨平台比较数字。
6. 任何小说正文除项目自身规则外，默认同时读取：`shared/RULES.md`、`shared/DIALOGUE_RULES.md`、`shared/HUMANIZER_RULES.md`、`shared/HUMANIZER_EVOLUTION.md`、`shared/PROSE_RULES.md`、`shared/META_NARRATIVE_RULES.md`。
7. 新章/大改稿默认依次经过：Dialogue Pass → `dialogue_guard.py` → Humanizer Pass → `humanizer_guard.py` → Prose Pass → `prose_guard.py` → `meta_narrative_guard.py` → 连续性/数字终审。
8. 去 AI 腔不是关键词替换任务。禁止为了通过检查机械碎句、强行口语化、批量改同义词或清除作品本来成立的排比、比喻和节奏。
9. 每本长期项目都应建立自己的正向 `STYLE_DNA`；有稳定人物对白时建立 `DIALOGUE_VOICES.md`；有作者认可样本后建立/维护 `VOICE_SAMPLES.md`。
10. 作者人工改稿、版本选择、读者明确语言反馈都属于长期训练数据，必须按 `HUMANIZER_EVOLUTION.md` 回写到单本 `HUMANIZER_FEEDBACK.md`，不能改完正文就丢。
11. Humanizer 规则必须有误杀边界与回归测试。规则越多不代表越好，要防止形成新的“规则腔”。
12. 任何新设定先过“作者自己是否想点”的测试。包装无法救活一个自己都不想看的核心幻想。

## 长期 Humanizer 机制

本仓库不采用“一条万能 prompt 去 AI 味”的方案，而采用可积累系统：

```text
禁止层：共享 AI 痕迹与文体底线
↓
语气层：单本 STYLE_DNA / DIALOGUE_VOICES / VOICE_SAMPLES
↓
初稿与 Dialogue / Humanizer / Prose 审核
↓
作者校稿或读者反馈
↓
保存改前→改后差异
↓
提炼候选规则并验证
↓
稳定后升级单本或 shared
↓
下一章从更新后的规则开始
```

现成的 `blader/humanizer`、`op7418/Humanizer-zh`、`Raymondhou0917/speak-human-tw` 只作为起点；本仓库最终规则以作者真实校稿记录和本项目验证为准。

> 仓库名只是工作区名称，不等于任何一本小说的正式书名。
