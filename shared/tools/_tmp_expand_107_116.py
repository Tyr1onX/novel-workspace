from pathlib import Path
import re

ROOT = Path('novels/endless-rail')


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')


# README
p = 'README.md'
s = read(p)
s = s.replace('- 第87～106章：2026-08-29 连续续写，并完成逐章审计与全量连续性复核；详见 `docs/audit-087-106.md`\n', '- 第87～106章：完成逐章审计与全量连续性复核；详见 `docs/audit-087-106.md`\n- 第107～116章：2026-09-01 按新 Narrative Pass 续写10章并完成全量门禁；详见 `docs/narrative-pass-audit-001-116-20260901.md`\n')
s = s.replace('- 最新仓库正文：第106章《七张需求单，今天只接两件急的》\n- 下一章：第107章\n', '- 最新仓库正文：第116章《门锁能开了，电池还在掉温》\n- 下一章：第117章\n')
s = s.replace('第106章进入第三卷第二篇“寒季供应”。当前核心问题已经从“接口能不能接”转向“同时出现多项真实需求时，有限燃料、货位、时间和专业资源先给谁”。', '第106～116章推进第三卷第二篇“寒季供应”：真实取舍已经落到72h最低能源线、固定站分担、K-17低温暂停与≤6t西侧备用线实战。第116章进一步把低温故障反馈到归途站自身：货运门挡水片、P-01收纳防水罩/红色提醒带和低温工具位进入试用，电池舱外侧检修门/金属骨架低温下降最快，等待第117章根据夜间数据完成有限寒季运输组件。')
s = s.replace('1. `chapters/volume-03/chapter-104.md`\n2. `chapters/volume-03/chapter-105.md`\n3. `chapters/volume-03/chapter-106.md`\n4. `docs/next-window-handoff.md`\n5. `docs/continuity-ledger.md`\n6. `docs/continuity-update-087-106.md`\n7. `docs/character-memory-ledger.md`\n8. `docs/character-memory-update-087-106.md`\n9. `docs/writing-rules.md`\n10. `docs/reading-payoff-rules.md`\n11. `docs/short-term-outline.md`\n12. `docs/long-term-outline.md`\n13. `docs/master-outline.md`\n14. `style/HUMANIZER_FEEDBACK.md`\n15. `shared/RULES.md`\n16. `shared/DIALOGUE_RULES.md`\n17. `shared/HUMANIZER_RULES.md`\n18. `shared/HUMANIZER_EVOLUTION.md`\n19. `shared/PROSE_RULES.md`\n20. `shared/META_NARRATIVE_RULES.md`', '1. `chapters/volume-03/chapter-113.md`\n2. `chapters/volume-03/chapter-114.md`\n3. `chapters/volume-03/chapter-115.md`\n4. `chapters/volume-03/chapter-116.md`\n5. `docs/next-window-handoff.md`\n6. `docs/continuity-update-107-116.md`\n7. `docs/character-memory-update-107-116.md`\n8. `docs/narrative-pass-audit-001-116-20260901.md`\n9. `docs/writing-rules.md`\n10. `docs/reading-payoff-rules.md`\n11. `docs/short-term-outline.md`\n12. `docs/development-blueprint-107-510.md`\n13. `docs/capability-growth-ledger.md`\n14. `docs/long-term-outline.md`\n15. `docs/master-outline.md`\n16. `style/HUMANIZER_FEEDBACK.md`\n17. `shared/NARRATIVE_PASS_RULES.md`\n18. `shared/RULES.md`\n19. `shared/DIALOGUE_RULES.md`\n20. `shared/HUMANIZER_RULES.md`\n21. `shared/PROSE_RULES.md`\n22. `shared/META_NARRATIVE_RULES.md`')
s = s.replace('`Dialogue → Humanizer → Prose → Meta → 人工复核`', '`Narrative Pass → Dialogue → Humanizer → Prose → Meta → Continuity → 人工复核`')
s = s.replace('本轮新增事实以第87～106章正文与 `continuity-update-087-106.md` 为准。', '第107章以后新增事实以当前正文、`continuity-update-107-116.md` 与最新审计文档为准。')
write(p, s)


# Chapter index: add 107-116 rows and replace current-state tail.
p = 'chapters/index.md'
s = read(p)
marker = '| 106 | 七张需求单，今天只接两件急的 | 2824 | 第三卷新稿·逐章审计通过 |\n'
rows = marker + '''| 107 | 六十四箱，今天先去麦丘 | 2935 | 第三卷新稿·Narrative Pass审计通过 |\n| 108 | 医疗两个字，今天先等 | 2905 | 第三卷新稿·Narrative Pass审计通过 |\n| 109 | 这条线以下不动 | 2801 | 第三卷新稿·Narrative Pass审计通过 |\n| 110 | 三只空水箱，自己回沉泉 | 2825 | 第三卷新稿·Narrative Pass审计通过 |\n| 111 | 今天归途站没发车 | 2865 | 第三卷新稿·Narrative Pass审计通过 |\n| 112 | 三十六箱，只跑到炉坪 | 2840 | 第三卷新稿·Narrative Pass审计通过 |\n| 113 | 先看时限，后面才看货名 | 2864 | 第三卷新稿·Narrative Pass审计通过 |\n| 114 | K-17回位慢了半秒 | 2893 | 第三卷新稿·Narrative Pass审计通过 |\n| 115 | 六吨以内，五公里过桥 | 2834 | 第三卷新稿·Narrative Pass审计通过 |\n| 116 | 门锁能开了，电池还在掉温 | 2924 | 第三卷新稿·Narrative Pass审计通过 |\n'''
if '| 107 | 六十四箱，今天先去麦丘' not in s:
    s = s.replace(marker, rows)
idx = s.find('## 当前状态')
if idx == -1:
    raise SystemExit('index current-state marker missing')
s = s[:idx] + '''## 当前状态

- 最新仓库正文：第116章《门锁能开了，电池还在掉温》。
- 下一章：第117章。
- 第107～116章去空白正文字符均为2801～2935，已完成 Narrative / Dialogue / Humanizer / Prose / Meta / Continuity 审计。
- 全书第1～116章 Narrative Pass 无剩余 heuristic review；Novel Gate `HARD=0`；Meta `hard=0 / warn=0`。
- 权威审计：`../docs/narrative-pass-audit-001-116-20260901.md`。
- 最新连续性：`../docs/continuity-update-107-116.md`。
- 最新人物记忆：`../docs/character-memory-update-107-116.md`。

## 第117章续写入口

按以下顺序读取：

1. `volume-03/chapter-113.md`
2. `volume-03/chapter-114.md`
3. `volume-03/chapter-115.md`
4. `volume-03/chapter-116.md`
5. `../docs/next-window-handoff.md`
6. `../docs/continuity-update-107-116.md`
7. `../docs/character-memory-update-107-116.md`
8. `../docs/narrative-pass-audit-001-116-20260901.md`
9. `../docs/short-term-outline.md`
10. `../docs/capability-growth-ledger.md`
11. `../../../shared/NARRATIVE_PASS_RULES.md`
12. `../../../shared/RULES.md`
13. `../../../shared/DIALOGUE_RULES.md`
14. `../../../shared/HUMANIZER_RULES.md`
15. `../../../shared/PROSE_RULES.md`
16. `../../../shared/META_NARRATIVE_RULES.md`

第117章只负责寒季供应篇的有限收束：读取第116章夜间电池温度对照，确认可验证的低温改造，并让货运门/P-01/低温工具位至少再承担一次真实使用。不得提前进入成熟保险/信用体系，也不得把西侧备用线写成常规主路。
'''
write(p, s)


# Short-term outline: advance authoritative state and replace 107-117 section.
p = 'docs/short-term-outline.md'
s = read(p)
s = s.replace('# 当前短期大纲：第106章后', '# 当前短期大纲：第116章后')
s = re.sub(r'> 当前起点：第106章.*?不能只跟上一章局部续写。', '> 当前起点：第116章《门锁能开了，电池还在掉温》完成。第三卷《联轨商路》进行中；下一章第117章。\n>\n> 本文件负责当前5～15章执行；中层与长期方向必须同时对齐 `development-blueprint-107-510.md` 和 `capability-growth-ledger.md`，不能只跟上一章局部续写。', s, count=1, flags=re.S)
start = s.find('# 第107～117章：寒季供应')
end = s.find('# 第118章以后自然入口')
if start == -1 or end == -1:
    raise SystemExit('short-term section markers missing')
replacement = '''# 第107～117章：寒季供应

## 已完成：107～109 真实取舍

- 107：麦丘64箱延期热粮包完成取货，下午生产线恢复原节拍；其他候选继续等待。
- 108：白栎防冻伤敷料虽带医疗标签，但宋雨眠根据真实库存明确可等；炉坪K-17低温道岔脂反而先影响生活/运输系统，白03只取已确认工务材料。
- 109：拟议完整路线压入72h最低能源余量，梁文山明确否决；沉泉空箱与白栎敷料改由固定站已有车辆/路线分担，归途站主体整日不动。

## 已完成：110～113 网络开始自己工作

- 沉泉维修车自行从炉坪带回S-31/S-32/S-33并继续本站清洗/水泵维修。
- 第111章归途站整日不发车，麦丘、暖桥、沉泉、白栎、炉坪、旧港仍各自运行。
- 麦丘36箱北岬热粮包拆成三段：归途站只跑麦丘→炉坪，白03负责炉坪→旧港，北岬黄牌车负责旧港→北岬。
- 第113章形成归途站内部寒季候选页，只记录最晚时间、拖延后果、本站替代、并线可能、最低余量；不评分，不按货物标签自动排序。

## 已完成：114～116 寒潮运输事件主体

- K-17低温回位出现2.1s / 2.4s / 2.3s，超过既有>2s暂停边界；赵琴撤销货运放行。
- 许成定位到加热回路松动压接；修复、复温和轻型工务车复检后，K-17恢复约1.7～1.8s并重新放行。
- 已承诺36箱热粮包改走西侧备用线：白03实称4.82t，继续遵守≤6t、排水桥5km/h单车不停车、炉坪登记与旧港接货窗口。
- 第二个人工道岔冻泥清除后才放车；旧港主动调整后续普通车辆窗口，货物完成入库；次日下午北岬黄牌车签收36箱。
- 西侧绕行线任务完成后退回备用状态，不升级为第二主路。
- 归途站自身已经出现并试用：货运门挡水片、P-01收纳防水罩+红色提醒带、低温工具位。
- 电池舱低温问题仍未解决：外侧检修门/金属骨架附近降温最快，外侧测点曾比内侧低6℃以上；已加临时对照点和门缝纸带检查。

## 第117章：寒季运输组件收束

**唯一主问题：第116章暴露的低温问题，哪些已经有足够数据变成可重复措施？**

必须：

- 先读一夜电池舱对照温度，区分门封渗风与金属冷桥的证据；
- 只用现有材料、能源和专业人员做有限改造，不封死通风、不乱裹保温棉、不凭空增加供能；
- 货运侧门挡水片、P-01收纳罩/红带、低温工具位至少在一次真实低温准备或货运中复用；
- 最终形成小型、可见、有限的【寒季运输组件】；不要一次塞满所有候选能力；
- 章末让读者能从开门、P-01、工具位置或电池低温状态直接看出归途站比106章更适合寒季运行。

禁止：

- 新系统白送万能恒温；
- 直接把电池舱问题归因到一个未经验证的原因；
- 把北岬无时限接触器硬拉进主线凑事件；
- 再开一次区域政策大会；
- 提前进入118～130的成熟信用/保险设计。

'''
s = s[:start] + replacement + s[end:]
write(p, s)


# Capability ledger: update current stage and replace cold-season section.
p = 'docs/capability-growth-ledger.md'
s = read(p)
s = s.replace('## 3. 自给型移动服务站（36～106，当前）', '## 3. 自给型移动服务站（36～116，当前）')
start = s.find('# 三、下一阶段：寒季运输强化（107～117）')
end = s.find('# 四、区域服务枢纽（118～145）')
if start == -1 or end == -1:
    raise SystemExit('capability section markers missing')
replacement = '''# 三、当前强化：寒季运输（107～117，已到116）

## 已验证/已进入试用

### 网络侧

- 72h最低能源余量已经真实否决外部完整路线；
- 固定站可用自己的车辆、库存、生产节拍和货位分担，不再默认由归途站包办；
- 西侧绕行线完成一次4.82t白03真实货运，仍维持≤6t、5km/h排水桥、炉坪登记等旧边界；
- K-17低温加热回路故障被发现、暂停、修复、复检，主路恢复后备用线退回后台。

### 归途站实体低温准备

- **货运侧门挡水片（试用）**：减少融水进入锁舌；连续低温夜晚后第一拉可开，仍需更多天气复用。
- **P-01收纳防水罩（试用）**：4只，仅收纳状态覆盖锁销槽上半面，底部排水开放；红色提醒带提示展开前取下。
- **低温工具位（已使用1次）**：塑料刮片、窄刷、吸水布、当前确认可用于P-01规定位置的小罐低温润滑脂；湿布外晾后再收。

### 尚未完成

- 牵引电池低温维持启动越来越早；外侧检修门/金属骨架附近降温最快。
- 已布置外壁、门框、舱内、铰链附近临时温度点；纸带提示下方铰链附近可能有轻微空气流动。
- 当前还不能确认主要损失来自门封渗风还是材料冷桥，因此没有直接加保温棉、封死通风或增加加热功率。

## 第117章完成条件

第117章只从以上已经发生的故障和测试形成有限【寒季运输组件】。至少做到：

1. 读取夜间电池温度数据并做有证据的有限处理；
2. 让货运门/P-01/低温工具位至少再有一次真实低温复用；
3. 保留所有原有安全与能源边界；
4. 读者不看系统框也能从列车操作上感到寒季准备已经成形。

寒季组件仍需后续真实任务累计第二、第三次复用，才能进入长期稳定能力。

'''
s = s[:start] + replacement + s[end:]
write(p, s)


# Rewrite next-window handoff as current authoritative concise handoff.
p = 'docs/next-window-handoff.md'
write(p, '''# 新窗口续写交接

> **权威状态：正文已写到第116章《门锁能开了，电池还在掉温》。第三卷《联轨商路》进行中；寒季供应篇只剩第117章收束。下一章：第117章。**

## 续写前必须读

1. `chapters/volume-03/chapter-113.md`
2. `chapters/volume-03/chapter-114.md`
3. `chapters/volume-03/chapter-115.md`
4. `chapters/volume-03/chapter-116.md`
5. 本文件
6. `docs/continuity-update-107-116.md`
7. `docs/character-memory-update-107-116.md`
8. `docs/narrative-pass-audit-001-116-20260901.md`
9. `docs/short-term-outline.md`
10. `docs/capability-growth-ledger.md`
11. `docs/development-blueprint-107-510.md`
12. `docs/writing-rules.md`
13. `docs/reading-payoff-rules.md`
14. `style/HUMANIZER_FEEDBACK.md`
15. `shared/NARRATIVE_PASS_RULES.md`
16. `shared/RULES.md`
17. `shared/DIALOGUE_RULES.md`
18. `shared/HUMANIZER_RULES.md`
19. `shared/PROSE_RULES.md`
20. `shared/META_NARRATIVE_RULES.md`

## 审计状态

- 第1～116章 Narrative Pass：无剩余 heuristic review 命中。
- 全书 Novel Gate：`HARD=0`。
- 全书 Meta Narrative：`hard=0 / warn=0`。
- 第107～116章字符数：2801～2935，均进入本书常规章目标区间附近。
- Soft WARN 只作人工复核提示，不为追求 WARN=0 改坏真实货单、工务步骤和人物合理纠正对白。

## 107～116已经发生

### 真实取舍

- 麦丘64箱延期热粮包已经完成取货，生产线恢复原节拍。
- 白栎两箱防冻伤敷料虽然带医疗标签，宋雨眠根据真实库存确认可等；医疗标签不自动获得绝对优先。
- 梁文山在第109章真实否决会压穿未来72h最低能源余量的完整路线。
- 沉泉空箱改由沉泉自己的维修车带回；白栎敷料通过白03 + 白栎转运车接力，归途站主体当天不发车。

### 网络开始自己工作

- 沉泉自己做空箱清洗、水泵维修和清水试运行。
- 暖桥自行巡检伴热带、保温层和扎带。
- 麦丘自己调整成品库和包装节拍。
- 炉坪继续掌握K-17、白03和西侧备用线实际放行。
- 旧港自己调整货位窗口；北岬黄牌车只承担北岬自己的路线。

### 麦丘36箱 → 北岬

三段权限继续分开：

1. 归途站：麦丘→炉坪；
2. 炉坪白03：炉坪→旧港；
3. 北岬黄牌车：旧港→北岬。

第113章下午K-17低温回位出现2.1s / 2.4s / 2.3s，超过>2s暂停边界；赵琴撤销货运放行。许成定位为加热回路松动压接，修复/复温后恢复约1.7～1.8s。

已承诺36箱没有硬闯主路：白03装货后实称**4.82t**，改走既有西侧备用线，继续遵守：

- 当前总重≤6t；
- 旧排水桥5km/h；
- 单车、不在桥上停车；
- 每次炉坪登记；
- 两个人工道岔现场确认；
- 旧港单独确认接货窗口。

货物成功到旧港，次日下午北岬黄牌车签收36箱。西侧线随即退回备用状态，没有变成常规第二主路。

## 第116章末实体状态

### 货运侧门

- 锁舌本身没有结构损坏；此前问题来自上沿进水后低温结冰。
- 已增加可拆橡胶挡水片，避开原下方排水口。
- 连续低温观察后第一拉可开；仍属于试用改造。

### P-01

- 融雪残水会沿收纳结构进入锁销槽并结霜。
- 已做4只**收纳防水罩**：只覆盖收纳时上半槽口，底部排水开放。
- 每只罩子加红色短提醒带，展开前必须取下。
- 已完成收纳→取罩→展开测试，黄圈全部收净；还需真实低温货运继续复用。

### 低温工具位

货运侧门旁现有：塑料刮片、窄刷、吸水布、小罐规定低温润滑脂；湿布通过旁边网袋外晾干再收。已经实际使用过一次。

### 电池舱——117的直接问题

- 低温静置时牵引电池预热启动越来越早。
- 外侧检修门/金属骨架附近降温最快；外侧测点曾比内侧低6℃以上。
- 已增加外壁、门框、舱内、下方铰链附近临时温度对照点。
- 纸带测试提示下方铰链附近可能存在轻微空气流动。
- **目前不能确认主要损失来自门封渗风还是金属冷桥。**
- 禁止直接乱裹保温棉、封死通风、凭空提高加热功率。

## 第117章唯一主目标

根据一夜真实温度曲线，把已经验证到足够程度的低温措施收束成一个**有限、可见、可复用的寒季运输组件**。

建议只选2～4项真实成立的东西，不要把候选全部塞满：

- 货运门关键锁止防水/除冰准备；
- P-01收纳防水罩 + 红色提醒带；
- 低温巡检工具位；
- 基于夜间数据确认后的有限电池舱处理。

117必须让其中至少一部分在真实低温准备/运输里再次使用。组件成立后仍要在后续任务中累计第二、第三次复用。

## 第118章以后

117收束寒季供应后，118进入第三卷下一篇“货物与信用”。优先从一次真实货损开始：货物状态 → 责任区间 → 信息隐瞒 → 一笔真实补偿/替代运输，再逐步长出有限保障规则。

禁止118开头直接做成熟保险系统、信用分面板或完整区域法规。

## 继续有效的硬边界

- 北岬外仓线：归途站**无直接通行授权**。
- 北岬2箱无时限接触器仍在旧港覆盖区，没有明确去向；不要硬拉来凑117事件。
- 白03属于炉坪维护廊，不属于归途站。
- 西侧绕行线仍≤6t且成本更高，只是备用路线。
- P-01日常轻货上限400kg，原型600kg静载不是使用上限；人员通行未评估。
- LV-01不是万能电源；AC-01不是通用220V接口线。
- 周野做路线/资源/协议选择；梁文山、周建国、许成、宋雨眠、蒋岑、赵琴/马立平等继续守各自专业边界。
- 沈青禾仍是白栎医疗技术员、30天轮班/考察身份，不是归途站医生。

## 写作流程

每个新章固定执行：

`Architecture Lite / QUD → First Draft → Narrative Pass → Dialogue → Humanizer → Prose → Meta → Continuity / Numbers → Final Read`

章末继续停在具体动作、设备、货物、数字、路线条件或未决问题，不写“本章意味着什么”。
''')
