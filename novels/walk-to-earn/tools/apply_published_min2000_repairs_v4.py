#!/usr/bin/env python3
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply_published_min2000_repairs import BLOCKS  # noqa: E402
from apply_published_min2000_repairs_v2 import EXTRA, body_chars, append_once  # noqa: E402

CHAPTERS = HERE.parent / "chapters"

FINAL_EXTRA = {
11: r'''
睡前沈川又看了一眼第二天的天气。青篁那边上午多云，山里温度比市区低几度。他把薄外套塞进包最外层，免得到时候为了省事不拿。

周航在群里问胡凯有没有登山杖，胡凯回说自己带一根，不够就不用。谁也没临时下单买装备。

沈川把手机调成静音。明天先到山脚，再决定身体是什么状态。
''',
13: r'''
第二天早上真正下楼时，沈川才知道昨天那种酸没有完全过去。前两级台阶还好，转到第三层以后，大腿前侧明显发紧。

他扶了一下栏杆，速度自然慢下来。周航走在后面，看到以后没笑，只说：“我也一样。”

两个人到楼下就各自去上班，没有谁提议把这点酸再走开。
''',
14: r'''
第二天中午，沈川照常在公司食堂点了平时那份饭。结账二十多块，他没有因为昨晚刚做完预算就改成最便宜的窗口。

预算只是告诉他钱去了哪里，不是让每顿饭都变成一道计算题。

吃完以后，他把电脑购物车里那台七千多的删掉，只保留两台真正会考虑的型号。等周五工资到账，再去线下摸一遍机器。
''',
16: r'''
交接表最后一栏签完，陈姐把文件拖回共享盘，问了一句：“实习证明月底开，电子版还是纸质？”

“电子版先给我就行。”

“可以。需要盖章纸质的提前说。”

“好。”

两个人说完各自回工位。沈川没有借这个机会再解释为什么不续一个月，决定已经说清楚了。
''',
17: r'''
六点前，沈川把第二天要穿的衬衫重新挂起来。领口有一道很浅的折痕，他用宿舍那只旧挂烫机过了两下。

周航路过时看见，停在门口：“你这个比我答辩还正式。”

“面试。”

“知道。”周航拿走插座上的充电头，“我只是没见你熨过衣服。”

沈川低头继续理袖口：“现在见了。”

周航没再接，拿着充电头回房。
''',
21: r'''
晚饭前，沈川把自己的自行车从楼下推出来试骑了一圈。车胎没问题，刹车也正常。暑假放久了，链条有点干，他在修车点加了几滴油。

师傅收五块钱。

明早如果起晚，就骑车；时间宽裕再走。这个选择不需要今晚提前决定。
''',
23: r'''
记录册合上以后，沈川又把第二天实验要带的两根线装进透明袋。上学期就发生过到了实验室才发现线留在宿舍的事，这次顺手一起收好。

桌边的自行车钥匙也放进包里。三个小时空课适合慢慢走，不代表第二天所有课间都适合。
''',
24: r'''
第二天早上胡凯翻到那一页时也看见了修正带。

“这里原来写错了？”

“单位。”

胡凯把自己的册子翻出来，对照原始数据看了两眼，也改了一处。老师还没进门，两个人改完就把本子收好，没有继续讨论昨天走了多少公里。
''',
25: r'''
第二天醒来时，地铁故障已经只是群聊里的一条旧通知。沈川照常骑车去上课，经过昨晚那个出站口时甚至没从那边走。

一次临时绕路就是一次临时绕路，不需要复制成习惯。
''',
31: r'''
第二天展示开始前十分钟，四个人才把两张海报真正贴上展板。胶点有一角不牢，胡凯重新按了一次。

老师进门以后，他们就停手坐下。前一晚没有熬到半夜继续改图，今天也没有因此少任何东西。
''',
}


def main() -> int:
    repaired = []
    residual = []
    targets = sorted(BLOCKS)

    for number in targets:
        path = CHAPTERS / f"chapter-{number:03d}.md"
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        before = body_chars(text)

        if before < 2000:
            text = append_once(text, f"<!-- min2000-repair-ch{number} -->", BLOCKS[number])
        if body_chars(text) < 2000 and number in EXTRA:
            text = append_once(text, f"<!-- min2000-repair-extra-ch{number} -->", EXTRA[number])
        if body_chars(text) < 2000 and number in FINAL_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-final-ch{number} -->", FINAL_EXTRA[number])

        after = body_chars(text)
        print(f"ch{number}: {before} -> {after}")
        if after < 2000:
            residual.append((number, after, 2000 - after))
            continue
        if after != before:
            path.write_text(text, encoding="utf-8")
            repaired.append((number, before, after))

    # Chapter 43 was already manually rewritten on this branch and may only
    # need its small branch-specific extension.
    p43 = CHAPTERS / "chapter-043.md"
    t43 = p43.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    b43 = body_chars(t43)
    if b43 < 2000 and 43 in EXTRA:
        t43 = append_once(t43, "<!-- min2000-repair-extra-ch43 -->", EXTRA[43])
    a43 = body_chars(t43)
    print(f"ch43: {b43} -> {a43}")
    if a43 < 2000:
        residual.append((43, a43, 2000 - a43))
    elif a43 != b43:
        p43.write_text(t43, encoding="utf-8")
        repaired.append((43, b43, a43))

    print("RESIDUAL_SHORTS=" + repr(residual))
    print("REPAIRED=" + repr(repaired))
    if residual:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
