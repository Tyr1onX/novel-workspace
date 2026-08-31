#!/usr/bin/env python3
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply_published_min2000_repairs import BLOCKS  # noqa: E402

ROOT = HERE.parent
CHAPTERS = ROOT / "chapters"

# Extra scene beats for chapters whose first substantive extension may still
# land too close to the 2000 hard floor. These are chapter-specific rather
# than generic padding.
EXTRA = {
7: r'''
临睡前，雨又敲了几下窗。沈川起身把阳台那双鞋往里面挪了半米，免得鞋头重新被打湿。回床时他没有带手机，屏幕就留在桌上充电。
''',
8: r'''
晚上收包时，沈川又把公司发的展馆交通说明看了一遍。早上地铁口到B3馆还有一段室内通道，主办方建议提前二十分钟到。他把这个时间留出来，没打算用“走快一点”去压缩。

新鞋鞋底还有前几天走路留下的灰。他用纸擦掉，工作证和一小包防磨贴放进同一个侧袋。第二天只是普通上班，真正需要站一天的是周三。
''',
13: r'''
鞋晾到阳台以后，沈川给自己倒了杯水。坐下来时腿一松，才发现今天最累的不是最后那一千多步，而是下午已经准备回家以后又重新往山里折返。

以后真遇到要找东西的情况还是会回去。只是这种路不能拿平路的步数去估体力。
''',
14: r'''
第二天早上，那几个账户还维持着昨晚的分法。沈川买早餐时照常付十几块，没有因为“预算”两个字突然改成什么都舍不得买。

真正让他觉得轻松的是另一件事：房租已经在那里，下个月吃饭的钱也在那里。剩下的钱可以买电脑，也可以不买；可以去砚海面试，也可以继续留着。至少每一个决定不用再和月底余额绑在一起。
''',
16: r'''
下午下班前，陈姐叫他确认最后一批交接权限。沈川照着清单一项项点，发现有个共享表还挂在自己个人账号下，又重新转给正式员工。

这件事比“简历被查看”更急。他把权限改完，截图留档，才关电脑下班。
''',
17: r'''
睡前沈川又把身份证摸了一遍，确认真的在钱包里，不是只记得“应该带了”。闹钟设两个，间隔五分钟。

做完这些，他把手机放远一点。第二天要走4.6公里还是坐车，到了砚海再决定；现在最重要的是别因为熬夜看路线把七点的车错过。
''',
18: r'''
回学校方向的地铁还有座。沈川坐下以后才感觉到今天一直绷着的肩膀慢慢松开。面试已经结束，返程也结束，剩下的事情至少要等周一。
''',
21: r'''
他又看了一眼宿舍到第一栋教学楼的骑行路线。共享单车早高峰不一定有，自己的车已经搬回学校，车锁钥匙就在抽屉里。

走、骑车、坐摆渡车，三种都能到。新学期第一天没必要提前把其中一种变成规定动作。
''',
22: r'''
睡前沈川下楼把修好的车重新捏了一遍后轮，气压正常。他把车停回棚里最里面的位置，免得第二天一早又被别人的车堵住。
''',
23: r'''
第二天早上胡凯真带了豆浆，杯子放到沈川桌上时已经不太热。

“昨天说的。”

“记性不错。”

胡凯坐下翻自己的记录册，发现同样那一栏单位也写错了，低声骂了一句，又拿笔改。两个人谁都没把十五块跑腿费再提起来。
''',
25: r'''
手机充上电以后，沈川顺手看了眼第二天的课程。第一节并不早，他没设额外闹钟。

六公里临时步行带来的疲劳不重，但脚底已经发热。沈川把鞋垫抽出来晾着，第二天照常骑车去教学楼，没必要把一次地铁故障变成新的日常路线。
''',
31: r'''
吃完晚饭，他把第二天展示要讲的三句话在脑子里过了一遍。海报只是辅助，真正要讲的内容还在他们自己的数据里。

确认没漏，沈川就去洗澡，没有把整个晚上重新花在一份已经做完的展示上。
''',
38: r'''
他把明早要带的课本塞进包里，顺手把跑鞋放回鞋柜。体测成绩会保留，腿上的酸也会自己退；今晚不需要再为“快了十七秒”安排一套新的训练计划。
''',
43: r'''
周六车票买完以后，沈川没有继续把砚海地图放大到每一条巷子。现在还只是去看看生活半径，真到毕业住哪里，至少还有好几个月。

他把招聘文件和车票放进同一个日历备注，手机调回静音。桌边那份晚饭盒已经空了，周航又戴上耳机开始下一轮在线题。

寝室里各忙各的，砚海也只是周末日历里多出来的一格。
''',
}


def body_chars(text: str) -> int:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    first = next(i for i, line in enumerate(lines) if line.strip())
    return len(re.sub(r"\s", "", "\n".join(lines[first + 1:]).strip()))


def append_once(text: str, marker: str, block: str) -> str:
    if marker in text:
        return text
    return text.rstrip() + "\n\n" + marker + "\n" + block.strip() + "\n"


def main() -> int:
    repaired = []
    for number, block in BLOCKS.items():
        path = CHAPTERS / f"chapter-{number:03d}.md"
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        before = body_chars(text)
        if before < 2000:
            text = append_once(text, f"<!-- min2000-repair-ch{number} -->", block)
        mid = body_chars(text)
        if mid < 2000 and number in EXTRA:
            text = append_once(text, f"<!-- min2000-repair-extra-ch{number} -->", EXTRA[number])
        after = body_chars(text)
        if after < 2000:
            raise RuntimeError(f"ch{number} still short: {before} -> {after}")
        if after != before:
            path.write_text(text, encoding="utf-8")
            repaired.append((number, before, after))
        print(f"ch{number}: {before} -> {after}")

    # Chapter 43 had an earlier manual rewrite on this branch; only extend it
    # if it remains below the newly enforced floor.
    p43 = CHAPTERS / "chapter-043.md"
    t43 = p43.read_text(encoding="utf-8")
    b43 = body_chars(t43)
    if b43 < 2000:
        t43 = append_once(t43, "<!-- min2000-repair-extra-ch43 -->", EXTRA[43])
        a43 = body_chars(t43)
        if a43 < 2000:
            raise RuntimeError(f"ch43 still short: {b43} -> {a43}")
        p43.write_text(t43, encoding="utf-8")
        repaired.append((43, b43, a43))
        print(f"ch43: {b43} -> {a43}")
    else:
        print(f"ch43: already {b43}")

    print(f"repaired={len(repaired)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
