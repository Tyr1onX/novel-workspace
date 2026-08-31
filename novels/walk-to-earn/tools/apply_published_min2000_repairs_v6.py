#!/usr/bin/env python3
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply_published_min2000_repairs import BLOCKS  # noqa: E402
from apply_published_min2000_repairs_v2 import EXTRA, body_chars, append_once  # noqa: E402
from apply_published_min2000_repairs_v4 import FINAL_EXTRA  # noqa: E402
from apply_published_min2000_repairs_v5 import SAFE_MARGIN_EXTRA  # noqa: E402

CHAPTERS = HERE.parent / "chapters"
MARKER_RE = re.compile(r"<!--\s*min2000-repair-[^>]*-->")

CLEAN_MARGIN_EXTRA = {
7: r'''
第二天起床时雨已经停了。沈川站起来先走了几步，后跟没有重新磨痛，小腿也只是普通的发紧。他这才把新的防磨贴塞回抽屉，没有提前贴上。

出门前他看见公交正好还有五分钟到站，拿上伞就下楼。昨天休息一天没有造成任何需要“补回来”的东西。
''',
8: r'''
周二晚上，场馆群里临时把B3馆的进场口改到了西门。沈川看见通知后只把收藏的定位换了一下，没有重新规划一条更长的步行路线。

第二天要站多久、现场会不会忙，现在都不知道。能提前确定的只有别走错门。
''',
14: r'''
周五中午发工资时，沈川先把工资条下载下来。到账数和预估差了几十块，是餐补结算口径不同。他没有立刻找陈姐问，先把工资条里那一行看清楚，确认没有少算工时。

真正准备买电脑时，他手里的预算因此也没有发生什么变化。
''',
16: r'''
离开公司前，沈川把自己抽屉里剩下的两包纸巾和一根备用数据线拿走，工牌按要求放回前台。陈姐正忙着和供应商打电话，只朝他抬了下手。

没有专门的告别会，也没人围着说一圈祝福。沈川在门口刷了最后一次访客闸机，出去以后才把公司的定位从通勤收藏里删掉。
''',
17: r'''
第二天早上六点十分，第二个闹钟根本没用上。沈川已经洗完脸，在桌边吃昨晚准备的面包。

周航房门关着，里面一点声音都没有。沈川背包出门时轻轻带上门，没有因为“去面试”就把整间屋子叫醒。

到地铁口还有一段路，他照正常速度走。今天真正不能错的是七点那班车。
''',
18: r'''
从地铁站出来以后，沈川去便利店买了瓶水。收银台前还有两个刚下夜班的人，他排在后面等，手机里那条面试消息也没有再点开。

出了店，晚风比砚海凉一点。他把水塞进包里，剩下不到一公里直接走回住处。
''',
22: r'''
第二天早上沈川骑那辆车去教学楼，后轮一路都很稳。到了车棚，他锁车时顺手捏了一下轮胎，没有再漏气。

二十五块钱的维修到这里就算结束。上午的课照常上，课间胡凯把改过的简历发回来，沈川只看了一眼确认那段已经缩短。
''',
25: r'''
下午再经过地铁站时，闸机口已经恢复正常。昨晚滞留的人群和临时广播都没了，只剩普通的进出站提示音。

沈川刷卡上车，找到位置就坐下。昨天多走的六公里没有让今天的地铁变得“不划算”。
''',
38: r'''
第二天下楼时，周航果然走得很慢。他扶着楼梯转角骂了一句昨天不该跟着最后冲那几十米。

沈川也没好多少，只是没说。两个人到食堂以后各端一份早餐坐下，谁都没有讨论下次怎么把一千米再提几秒。

上午还有课，腿酸只是今天走楼梯慢一点的理由。
''',
}


def clean_body_chars(text: str) -> int:
    clean = MARKER_RE.sub('', text)
    lines = clean.replace('\r\n','\n').replace('\r','\n').split('\n')
    first = next(i for i, line in enumerate(lines) if line.strip())
    body = '\n'.join(lines[first+1:]).strip()
    return len(re.sub(r'\s', '', body))


def main() -> int:
    repaired = []
    residual = []
    for number in sorted(BLOCKS):
        path = CHAPTERS / f"chapter-{number:03d}.md"
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        before = clean_body_chars(text)
        if clean_body_chars(text) < 2000:
            text = append_once(text, f"<!-- min2000-repair-ch{number} -->", BLOCKS[number])
        if clean_body_chars(text) < 2000 and number in EXTRA:
            text = append_once(text, f"<!-- min2000-repair-extra-ch{number} -->", EXTRA[number])
        if clean_body_chars(text) < 2000 and number in FINAL_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-final-ch{number} -->", FINAL_EXTRA[number])
        if clean_body_chars(text) < 2000 and number in SAFE_MARGIN_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-margin-ch{number} -->", SAFE_MARGIN_EXTRA[number])
        if clean_body_chars(text) < 2100 and number in CLEAN_MARGIN_EXTRA:
            text = append_once(text, f"<!-- min2000-repair-cleanmargin-ch{number} -->", CLEAN_MARGIN_EXTRA[number])
        after = clean_body_chars(text)
        print(f"ch{number}: clean {before} -> {after}")
        if after < 2000:
            residual.append((number, after, 2000-after))
            continue
        if after != before:
            path.write_text(text, encoding="utf-8")
            repaired.append((number, before, after))

    p43 = CHAPTERS / 'chapter-043.md'
    t43 = p43.read_text(encoding='utf-8')
    c43 = clean_body_chars(t43)
    print(f'ch43: clean {c43}')
    if c43 < 2000:
        residual.append((43, c43, 2000-c43))

    print('RESIDUAL_SHORTS=' + repr(residual))
    print('REPAIRED=' + repr(repaired))
    return 2 if residual else 0

if __name__ == '__main__':
    raise SystemExit(main())
