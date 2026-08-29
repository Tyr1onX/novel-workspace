#!/usr/bin/env python3
"""One-shot exact repair for Endless Rail meta-narrative leaks found on 2026-08-29.

Every replacement is exact and must occur once. The script aborts if the
expected source text is missing or duplicated, so it cannot silently drift.
"""

from pathlib import Path

ROOT = Path("novels/endless-rail/chapters")

REPAIRS = {
    "volume-01/chapter-023.md": [
        (
            "他调出第十二章铺设临时钢轨桥时留下的结构记录。",
            "他调出此前铺设临时钢轨桥时留下的结构记录。",
        ),
    ],
    "volume-02/chapter-072.md": [
        (
            "第31章时，旧港发来的第一条正式消息，就是要求外来列车提交完整成员和库存。",
            "最早收到旧港那条正式消息时，对方要求外来列车提交完整成员和库存。",
        ),
    ],
    "volume-02/chapter-087.md": [
        (
            "孙晓雨把第86章谈好的条件调出来。",
            "孙晓雨把N-3-4开始前谈好的条件调出来。",
        ),
        (
            "这一次，正文里不需要再守着它每半小时称一次。",
            "这一次，许成没再让人守着它每半小时称一次。",
        ),
        (
            "“剩下按货单走，别再一只一只写成长试验。”",
            "“剩下按货单走，别再一只一只从头做完整试验。”",
        ),
    ],
    "volume-02/chapter-088.md": [
        (
            "这一只已经没有继续展开的必要。",
            "这一只已经没有继续处理的必要。",
        ),
        (
            "三只没有再复制B17、B21、C09的完整过程。",
            "三只都按各自状态处理，没有照搬B17、B21、C09的全部步骤。",
        ),
    ],
    "volume-02/chapter-089.md": [
        (
            "他已经有一段时间没进入北岬滤筒的剧情，回到燃料问题时，手里先拿的是归途站自己的储备表。",
            "北岬滤筒任务结束后，梁文山一直在盯归途站自己的能源账；这次一进来，手里先拿的也是储备表。",
        ),
    ],
    "volume-02/chapter-090.md": [
        (
            "正好占满第89章确认的三个位置。",
            "正好占满前一天确认的三个临时位置。",
        ),
        (
            "第89章那句“按实际占用”第一次落到了数字上。",
            "前一天定下的“按实际占用”第一次落到了数字上。",
        ),
    ],
    "volume-02/chapter-091.md": [
        (
            "第一部分是上一章已经发生的燃料运输前后检查。",
            "第一部分是刚完成的燃料运输前后检查。",
        ),
    ],
    "volume-02/chapter-092.md": [
        (
            "他没有沿用第71章东联络桥那次“十八吨以下”的数据。",
            "他没有沿用此前东联络桥那次“十八吨以下”的数据。",
        ),
        (
            "孙晓雨翻出上一章称重。",
            "孙晓雨翻出前一批燃料车的称重记录。",
        ),
    ],
    "volume-02/chapter-093.md": [
        (
            "白栎医疗负责人宋雨眠隔了很长一段剧情后重新接入。",
            "白栎医疗负责人宋雨眠很久没有直接接入归途站的运输通信，这次重新上线。",
        ),
    ],
    "volume-02/chapter-094.md": [
        (
            "孙晓雨没有把这段话写进正文式总结。",
            "孙晓雨没再另写说明。",
        ),
    ],
    "volume-03/chapter-096.md": [
        (
            "“电的我晚一章。”",
            "“电的我往后排。”",
        ),
        (
            "“你还给自己排章？”",
            "“你还给自己排顺序？”",
        ),
    ],
    "volume-03/chapter-097.md": [
        (
            "上一卷留下的送修任务在这块新桥板上完成回送。",
            "此前留下的送修任务在这块新桥板上完成回送。",
        ),
    ],
    "volume-03/chapter-098.md": [
        (
            "上一卷北岬结算送来的八米灯条还剩一卷。",
            "N-3-4结算时北岬送来的八米灯条还剩一卷。",
        ),
    ],
    "volume-03/chapter-099.md": [
        (
            "上一章六分钟接电，这次压到四分钟以内。",
            "上一次六分钟接电，这次压到四分钟以内。",
        ),
    ],
    "volume-03/chapter-101.md": [
        (
            "第99章那一班把暖桥第二台生活水泵送回去以后，前两天都没再报故障。",
            "暖桥第二台生活水泵上次送回去以后，前两天都没再报故障。",
        ),
        (
            "维修没有因此变成另一条长剧情。",
            "维修范围到这里就收住了。",
        ),
    ],
    "volume-03/chapter-103.md": [
        (
            "这项直接接进第102章的跨站对象索引。",
            "这项直接接进刚启用的跨站对象索引。",
        ),
        (
            "第89章那批低温柴油陆续转入归途站以后，空桶开始回到炉坪。",
            "前一批低温柴油陆续转入归途站以后，空桶开始回到炉坪。",
        ),
    ],
    "volume-03/chapter-104.md": [
        (
            "P-01在第97章正式班次验证以后，日常轻货已经允许受训人员操作。",
            "P-01完成正式班次验证以后，日常轻货已经允许受训人员操作。",
        ),
    ],
    "volume-03/chapter-105.md": [
        (
            "对象号来自第102章拆出来的B子项。",
            "对象号来自之前拆出的B子项。",
        ),
        (
            "第二班那只沉泉借给暖桥的阀，因为在第102章已经归还，不会再短暂出现在归途站“可用阀门”列表里。",
            "第二班那只沉泉借给暖桥的阀已经完成归还，不会再短暂出现在归途站“可用阀门”列表里。",
        ),
    ],
}


def main() -> int:
    total = 0
    for relative, replacements in REPAIRS.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in replacements:
            count = text.count(old)
            if count != 1:
                raise SystemExit(f"{path}: expected exactly 1 occurrence, found {count}: {old}")
            text = text.replace(old, new, 1)
            total += 1
        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"repaired {path}: {len(replacements)}")
    print(f"total replacements={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
