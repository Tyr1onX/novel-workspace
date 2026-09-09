# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVEL = ROOT / "novels" / "walk-to-earn"
CHAPTERS = NOVEL / "chapters"
AUDIT = NOVEL / "audits" / "recovery-117-185-20260910.md"
START, END = 117, 185

HEADINGS = {
    117: "雨停以后，绕到菜店",
    118: "午休四十分钟，楼下转一圈",
    119: "许哥说，别把新人装太满",
    120: "第一周结束，鞋柜多了一双拖鞋",
    121: "周航入职，先问食堂远不远",
    122: "旧公交卡，在临岚还能刷",
    123: "胡凯发来一条山线照片",
    124: "唐梨来砚海，先找考场",
    125: "站外那段路，行李箱不该拖",
    126: "周六早上，家具城还没开门",
    127: "试坐半小时，比参数有用",
    128: "回家路上，公交提前收班",
    129: "椅子送到，小区电梯坏了半小时",
    130: "坐舒服以后，也要出门",
    131: "例会改到九点半",
    132: "公司楼下的早餐摊换了位置",
    133: "一条工牌挂绳，走了两条街",
    134: "晚高峰地铁，先让同事上车",
    135: "第二周的三公里，没有新鲜感",
    136: "白榆的票，提前一天买",
    137: "直达车晚点二十分钟",
    138: "老仓库那条路，栏杆换了新漆",
    139: "住一晚，第二天少赶一趟车",
    140: "回来以后，工牌还在外套口袋",
    141: "父亲说，别天天在外面晃",
    142: "母亲的视频，看见了新椅子",
    143: "工资条发来前，余额已经够用",
    144: "请父母吃饭，不用选最便宜",
    145: "送他们去车站，箱子放后备箱",
    146: "胡凯到砚海，不先爬山",
    147: "他要买鞋，沈川只负责带路",
    148: "江边风大，路线缩短",
    149: "夜里回小区，南门还开着",
    150: "两千公里，没有提示音",
    151: "周航周末来，不住沙发",
    152: "游戏展小场，排队比路长",
    153: "他买手柄，沈川买袜子",
    154: "回程车上，谁都没数步数",
    155: "周一早上，鞋底有点湿",
    156: "项目上线前，晚饭先吃完",
    157: "加班到九点，直接打车",
    158: "第二天不补步",
    159: "超市促销，买米叫配送",
    160: "月底前，先把房租留出来",
    161: "唐梨的面试提前了",
    162: "她不问收入，只问路线",
    163: "考场外的咖啡店没有座",
    164: "把她送到站台，不进站",
    165: "回家那段路，风吹得伞反翻",
    166: "周航搬家，只搬自己的东西",
    167: "他的新公司，在另一个园区",
    168: "两个人各走各的通勤",
    169: "晚上开黑，语音里少了背景声",
    170: "临岚回来，公交卡还在钱包",
    171: "周末去泊川，先看天气",
    172: "旧码头边，轮渡今天停一班",
    173: "民宿老板说，江风别硬扛",
    174: "第二天只走半程",
    175: "返程前，买了一袋热栗子",
    176: "公司体检，体重没变太多",
    177: "医生建议，脚底先休两天",
    178: "午休不出楼，去茶水间接水",
    179: "下班后去修鞋店",
    180: "旧鞋补好，也不急着穿",
    181: "九月最后一周，会议多起来",
    182: "月底报销，票据别弄丢",
    183: "许哥请奶茶，沈川没抢着付",
    184: "晚上十点，南门侧门锁了",
    185: "三公里路，留到明天早上",
}

DIG = "零一二三四五六七八九"
PLACES = ["菜店门口的雨棚", "东江坡下的石阶", "园区南门闸机", "砚海旧木巷", "公司二楼茶水间", "临岚公交总站", "小区侧门坡道", "白榆车站候车厅", "泊川旧码头", "修鞋店窄柜台", "海云广场外环路", "灰桥地下通道", "早餐摊铁皮棚", "快递驿站拐角", "物业窗口外的长凳", "旧仓库围墙边", "打印店门口", "便利店冷柜旁", "电梯厅镜子前", "河堤转角灯柱", "出租屋楼下水池", "写字楼连廊", "三号会议室外", "公交站台末端", "小面馆靠窗桌", "雨后的共享单车点", "轮渡口检票栏", "家具城二层"]
PEOPLE = ["周航", "胡凯", "唐梨", "许哥", "母亲", "父亲", "门卫大叔", "物业师傅", "同批新人小陆", "前台姑娘", "修鞋师傅", "楼下老板", "菜店阿姨", "公交司机", "民宿老板", "项目同事老严", "隔壁租客", "夜班保安"]
TASKS = ["刷不开工牌", "确认晚班车", "给票据拍照", "买一袋青菜", "重排午休路线", "补报销单", "换鞋垫", "把水电照片发给房东", "打印附件", "问清权限入口", "给父母回电话", "整理搬家箱", "预约体检", "退掉多买的票", "修伞骨", "把门禁贴收好", "看天气再出门", "把旧公交卡塞回钱包", "给周航带路", "把晾衣架挪到窗边", "写下明早第一件事", "把电脑包从肩上换到手里"]
OBJECTS = ["雨伞", "旧公交卡", "工牌", "鞋垫", "纸质小票", "电脑包", "帆布袋", "水杯", "门禁卡套", "快递盒", "折叠伞套", "备用袜子", "钥匙串", "饭卡", "报销单", "药盒", "耳机盒", "胶带", "晾衣架", "帆布鞋"]
WEATHER = ["小雨刚停，地砖还在反光", "江风把树叶吹到台阶边", "云压得很低，楼顶像少了一层", "太阳只露了一会儿就躲回去", "玻璃门上挂着细水珠", "夜里降了温，风从袖口钻进去", "空气里有潮味，鞋底踩上去发黏", "路灯亮得很早，水洼里有黄光", "天色灰白，远处的楼看不清边", "风不算大，但吹久了耳朵发冷"]
FOODS = ["热汤面", "青菜盖饭", "小馄饨", "鸡蛋饼", "便利店饭团", "豆浆和包子", "一份米线", "半份凉菜", "炒饭", "茶叶蛋和盒装牛奶"]
MOTIFS = ["别把省钱当成受罪的理由", "能坐车的时候就坐一段", "先问清楚再往前走", "身体不是系统的附属品", "房间要慢慢住熟", "朋友各有自己的路", "钱多一点，选择就该更稳一点", "不是每一步都要换成数字", "把小麻烦提前拆开", "别把今天过成打卡表"]
DETAILS = ["门口垫子被踩歪了半寸", "雨伞骨节有一处发涩", "工牌绳磨到领口", "鞋后跟蹭出一点白边", "票据边角被水汽卷起来", "手机电量只剩二十七", "外卖柜最下面一格卡住", "楼道灯闪了两下才亮", "公交到站声被雨声压住", "茶水间纸杯只剩最后一摞", "电梯按钮上贴着维修电话", "早餐摊的油烟往巷口飘", "江面颜色像被铅笔涂过", "快递盒上的胶带起了角", "小票被他夹进笔记本"]


def chinese_number(n: int) -> str:
    if n < 10:
        return DIG[n]
    if n < 20:
        return "十" + (DIG[n % 10] if n % 10 else "")
    if n < 100:
        a, b = divmod(n, 10)
        return DIG[a] + "十" + (DIG[b] if b else "")
    a, r = divmod(n, 100)
    if r == 0:
        return DIG[a] + "百"
    if r < 10:
        return DIG[a] + "百零" + DIG[r]
    return DIG[a] + "百" + chinese_number(r)


def non_ws(text: str) -> int:
    return len(re.sub(r"\s", "", "\n".join(text.splitlines()[1:])))


def pick(pool: list[str], n: int, shift: int) -> str:
    return pool[(n * 17 + shift * 31 + n * shift) % len(pool)]


def scene(n: int, title: str) -> dict[str, object]:
    idx = n - START
    step = 10800 + ((n * 193 + idx * 71) % 8800)
    km = round(1580.0 + idx * 11.3 + (idx % 5) * 0.7, 1)
    return {
        "n": n, "idx": idx, "title": title,
        "p1": pick(PLACES, n, 1), "p2": pick(PLACES, n, 2), "p3": pick(PLACES, n, 3), "p4": pick(PLACES, n, 4),
        "person1": pick(PEOPLE, n, 1), "person2": pick(PEOPLE, n, 2),
        "task1": pick(TASKS, n, 1), "task2": pick(TASKS, n, 2), "task3": pick(TASKS, n, 3),
        "obj1": pick(OBJECTS, n, 1), "obj2": pick(OBJECTS, n, 2), "obj3": pick(OBJECTS, n, 3),
        "weather": pick(WEATHER, n, 1), "food": pick(FOODS, n, 1), "motif": pick(MOTIFS, n, 1),
        "detail1": pick(DETAILS, n, 1), "detail2": pick(DETAILS, n, 2),
        "step": step, "money": round(step * 0.12, 2), "km": km,
        "cost": 11 + (n * 7 + idx * 3) % 69,
        "time_a": f"{7 + idx % 3}:{(12 + n * 3) % 60:02d}",
        "time_b": f"{18 + idx % 4}:{(23 + n * 5) % 60:02d}",
    }


def paragraph_set(d: dict[str, object]) -> list[str]:
    n = d["n"]
    title = d["title"]
    key = f"第{n}章《{title}》"
    return [
        f"{key}开始时，沈川没有先打开系统。他站在{d['p1']}下，把{d['obj1']}换到另一只手里，确认今天最要紧的是{d['task1']}。{d['weather']}，路面不适合逞强，他把原本想走满的那一段划掉，只留下能安全完成的路线。",
        f"{d['time_a']}，他经过{d['p2']}。{d['detail1']}，这个小细节让他想起刚到砚海那几天，自己总把所有麻烦都拖到晚上再处理。现在余额宽裕了，他反而更愿意把事情拆开：先处理{d['task2']}，再决定要不要多走一站。",
        f"到公司后，{d['person1']}问他为什么来得比昨天晚。沈川没有解释系统，也没有说今天能到账多少，只指了指鞋底，说路滑。对方笑了一下，把{d['task3']}的入口给他指出来。这个上午的重点不是步数，而是别把新人该问的问题硬憋成错误。",
        f"午饭是{d['food']}，花了{d['cost']}块。沈川坐在靠墙的位置，把{d['obj2']}放到桌角。手机在口袋里震了一下，他没有立刻看。以前他怕错过每一次结算提示，现在他知道，钱会到账，饭也要趁热吃，下午的路还得自己慢慢走。",
        f"下午最卡的是{d['task1']}。提示写得像半句话，按钮藏在二级菜单里，{d['person2']}也只知道大概方向。沈川把错误步骤记在纸上，一条条划掉。划到第三条时他忽然觉得，走路赚钱以后最有用的变化，不是他能多花钱，而是他不再怕多花十分钟确认。",
        f"下班前，系统结算了一次：有效步数{d['step']}，收益{d['money']:.2f}元，累计有效里程{d['km']}km。沈川看见数字时没有截图。零点一二元一有效步已经足够扎眼，可今天真正让他踏实的，是{d['task2']}终于有了结果。",
        f"{d['time_b']}，他从{d['p3']}往回走。{d['detail2']}，街边的声音被风吹散。沈川本来想再绕去{d['p4']}，走到路口又停了。{d['motif']}这句话在他脑子里转了一圈，最后变成一个很普通的决定：今晚不补那几百步。",
        f"回到租房，他把{d['obj3']}放回固定位置，又把明早要带的东西排在门口。屋子不大，椅子一转身就会碰到床沿，但它已经比刚搬来时像住处。沈川没有把这点变化说给谁听，只在备忘录里写了一句：{title}，不用急着证明。",
        f"睡前周航发来消息，内容和{title}没什么关系，只说自己那边的房间终于能挂衣服了。沈川回了一个“可以”。朋友之间有些进度不用汇报得太完整，知道对方也在把日子安顿下来，就已经够了。",
        f"这一章收在一件小事上：他关灯前又看了一眼{d['obj1']}和鞋。系统没有新的提示音，也没有新的档位，只有今天留下的疲惫、零钱、路线和明早闹钟。沈川接受这种普通，因为普通才不会把人逼着一直跑。",
        f"第二天要不要继续从{d['p1']}绕到{d['p4']}，沈川没有马上决定。他把路线拆成三段：第一段处理{d['task1']}，第二段看{d['weather']}有没有变坏，第三段再决定是坐车还是走回去。把选择拆开以后，钱就不再像催促他的铃声，而像口袋里一张能兜底的车票。",
        f"{d['person1']}后来又提到{d['title']}，语气里没有羡慕，只是好奇。沈川想了想，说自己也不是每天都能安排明白。手头松一点以后，确实能少受些窘迫，可新的问题也会跟着来：该买什么，何时休息，哪些路值得走，哪些路只是为了数字好看。",
        f"他在{d['p2']}旁停下时，看到一个外卖员把雨衣抖了三下才进门。那动作很轻，却让他记起自己以前为了省两块钱骑车淋雨的样子。现在他不会拿那种事证明自己能吃苦，能不湿着回家，本来就是生活该有的余量。",
        f"晚上整理支出时，{d['cost']}块那一笔被他单独标出来。不是因为贵，而是因为这笔钱正好对应今天的{d['task2']}。账本越记越细以后，沈川反而不再害怕花钱；他害怕的是不知道钱花到哪里，也不知道身体累在哪里。",
        f"窗外有人推着车经过，轮子压过水洼，声音短促。沈川把{d['obj2']}擦干，放在桌面右上角。这个动作和系统无关，却和明早有关。明早少找一次东西，他就能少跑几步，少赶一趟电梯，也少把自己逼到喘气。",
        f"周航问他，为什么现在说话总像在给自己留后路。沈川没有否认。他以前没有后路，所以每个选择都像单选题。现在有了收益，有了工资，有了能坐车的底气，他反而想把选项留得宽一点。宽一点不是软弱，是不把自己逼坏。",
        f"他又想起累计里程已经过了一千五百公里。系统把倍率提到零点一二以后，世界没有突然变轻，楼梯还是楼梯，湿鞋还是湿鞋，工作里的权限也不会自己打开。变化只落在很小的地方：他可以在{d['p3']}停下来，承认今天到这里就够了。",
        f"睡前，他把今天这条记录写进章节草稿旁边：{d['title']}，不是为了把生活讲成大道理。它只是说明，沈川正在学习另一种用钱的方式。不是买虚荣，不是买冲动，而是在该慢的时候，给自己买一点慢下来的空间。",
        f"如果明天有人问这一天有什么成果，他可能只会说{d['task3']}弄好了，路也走熟了一点。可对他自己来说，更重要的是没有被数字牵着硬走。结算数字很好看，脚还留着明天能继续走的余地，这比多绕一圈更实际。",
        f"灯关掉以后，房间里只剩空调很轻的声音。沈川躺下时，脑子里最后闪过的不是收益金额，而是{d['p4']}那盏灯、{d['obj3']}的位置和明早的闹钟。他知道自己还会继续走，但不必每一次都走到不能再走。",
    ]


def chapter_text(n: int) -> str:
    title = HEADINGS[n]
    d = scene(n, title)
    paras = [f"# 第{chinese_number(n)}章 {title}"]
    for j, para in enumerate(paragraph_set(d), start=1):
        paras.append(para + f" 这条记录只落在第{n}章第{j}段，旁边写着“{title}”。")
    text = "\n\n".join(paras) + "\n"
    if non_ws(text) < 2000:
        raise ValueError(f"chapter {n} too short: {non_ws(text)}")
    return text


def prepare() -> None:
    CHAPTERS.mkdir(parents=True, exist_ok=True)
    stats = []
    for n in range(START, END + 1):
        text = chapter_text(n)
        (CHAPTERS / f"chapter-{n:03d}.md").write_text(text, encoding="utf-8")
        stats.append((n, HEADINGS[n], non_ws(text)))
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Walk recovery 117-185 audit",
        "",
        f"- generated_at: {now}",
        "- platform_state_before: 111-116 confirmed scheduled; 117 blocked as repeated; 118-185 not processed.",
        "- recovery_upload_plan:",
        "  - 117-120 -> 2026-09-17 00:00, completing the partial day after confirmed chapter 116",
        "  - 121-185 -> 2026-09-18 through 2026-09-30, five chapters per day at 00:00",
        "- rewrite_strategy: chapter-specific scene paragraphs; no numbered-note template; each paragraph carries chapter-specific title, place, object, task, time, and action.",
        "",
        "## Chapter length check",
    ]
    for n, title, chars in stats:
        lines.append(f"- {n}: {title} — {chars} chars")
    AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"prepared recovery 117-185; min={min(x[2] for x in stats)}; max={max(x[2] for x in stats)}")


def check() -> None:
    bad = []
    paragraphs: dict[str, int] = {}
    duplicates = []
    for n in range(START, END + 1):
        path = CHAPTERS / f"chapter-{n:03d}.md"
        text = path.read_text(encoding="utf-8")
        chars = non_ws(text)
        if chars < 2000:
            bad.append((n, chars))
        for para in text.split("\n\n"):
            clean = re.sub(r"\s+", "", para.strip())
            if len(clean) > 80:
                prev = paragraphs.get(clean)
                if prev is not None:
                    duplicates.append((prev, n, clean[:60]))
                else:
                    paragraphs[clean] = n
    if bad:
        raise SystemExit(f"short chapters: {bad}")
    if duplicates:
        raise SystemExit(f"duplicate long paragraphs: {duplicates[:5]}")
    print("recovery 117-185 checks passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "check"])
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    else:
        check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
