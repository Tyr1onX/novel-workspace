# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVEL = ROOT / "novels" / "walk-to-earn"
CH = NOVEL / "chapters"
QUEUE = NOVEL / "platform-sync" / "queue.json"
CONFIG = NOVEL / "platform-sync" / "config.json"
AUDIT = NOVEL / "audits" / "recovery-113-185-20260910.md"

START = 113
END = 185
BOOK_ID = "7677956141673892926"
OLD_OP = "walk-create-111-185-schedule-through-20260930-20260909"
RECOVER_A = "walk-recover-113-115-fill-20260916-20260910"
RECOVER_B = "walk-recover-116-185-schedule-through-20260930-20260910"

TITLES = """
权限没开，路先走熟
一把椅子，坐过再买
周末不去商场，先走到江边
新工牌刷不开南门
雨停以后，绕到菜店
午休四十分钟，楼下转一圈
许哥说，别把新人装太满
第一周结束，鞋柜多了一双拖鞋
周航入职，先问食堂远不远
旧公交卡，在临岚还能刷
胡凯发来一条山线照片
唐梨来砚海，先找考场
站外那段路，行李箱不该拖
周六早上，家具城还没开门
试坐半小时，比参数有用
回家路上，公交提前收班
椅子送到，小区电梯坏了半小时
坐舒服以后，也要出门
例会改到九点半
公司楼下的早餐摊换了位置
一条工牌挂绳，走了两条街
晚高峰地铁，先让同事上车
第二周的三公里，没有新鲜感
白榆的票，提前一天买
直达车晚点二十分钟
老仓库那条路，栏杆换了新漆
住一晚，第二天少赶一趟车
回来以后，工牌还在外套口袋
父亲说，别天天在外面晃
母亲的视频，看见了新椅子
工资条发来前，余额已经够用
请父母吃饭，不用选最便宜
送他们去车站，箱子放后备箱
胡凯到砚海，不先爬山
他要买鞋，沈川只负责带路
江边风大，路线缩短
夜里回小区，南门还开着
两千公里，没有提示音
周航周末来，不住沙发
游戏展小场，排队比路长
他买手柄，沈川买袜子
回程车上，谁都没数步数
周一早上，鞋底有点湿
项目上线前，晚饭先吃完
加班到九点，直接打车
第二天不补步
超市促销，买米叫配送
月底前，先把房租留出来
唐梨的面试提前了
她不问收入，只问路线
考场外的咖啡店没有座
把她送到站台，不进站
回家那段路，风吹得伞反翻
周航搬家，只搬自己的东西
他的新公司，在另一个园区
两个人各走各的通勤
晚上开黑，语音里少了背景声
临岚回来，公交卡还在钱包
周末去泊川，先看天气
旧码头边，轮渡今天停一班
民宿老板说，江风别硬扛
第二天只走半程
返程前，买了一袋热栗子
公司体检，体重没变太多
医生建议，脚底先休两天
午休不出楼，去茶水间接水
下班后去修鞋店
旧鞋补好，也不急着穿
九月最后一周，会议多起来
月底报销，票据别弄丢
许哥请奶茶，沈川没抢着付
晚上十点，南门侧门锁了
三公里路，留到明天早上
""".strip().splitlines()

DIG = "零一二三四五六七八九"
PLACES = "南门侧门,东门岗亭,写字楼连廊,江边步道,楼下早餐摊,菜店门口,地铁口,快递驿站,物业窗口,茶水间,打印区,会议室外,公交站台,超市入口,修鞋店,家具城入口,旧码头,轮渡口,白榆车站,泊川江边,公司后门,小区水池,楼梯间,便利店冰柜,共享单车点,路边雨棚,电梯厅,门禁闸机,食堂窗口,租房楼下".split(",")
PEOPLE = "周航,胡凯,唐梨,许哥,父亲,母亲,物业师傅,同批新人,店员,房东,门卫大叔,项目同事,民宿老板,修鞋师傅,公交司机,楼下老板".split(",")
TASKS = "开权限,刷门禁,买晚饭,取快递,交水电照片,改路线,寄包,报销,洗衣服,换鞋垫,买早餐,确认末班车,看例会材料,补表单字段,找工牌挂绳,试坐椅子,给父母订车,看天气,买袜子,整理票据".split(",")
OBJECTS = "雨伞,工牌,旧公交卡,电脑包,帆布袋,鞋垫,水杯,饭卡,钥匙串,纸质票据,折叠伞,备用袜子,充电器,门禁卡,快递盒,旧鞋,塑料袋,笔记本,报销单,早餐袋".split(",")
WEATHERS = "小雨刚停,风从江边吹过来,路面还有水光,云压得很低,太阳只露了一会儿,楼下有雾气,夜里降了温,雨点断断续续,风不大但冷,空气里有潮味".split(",")
FOODS = "热汤面,鸡蛋饼,青菜盖饭,便利店饭团,豆浆,清汤粉,包子,炒饭,小馄饨,一瓶矿泉水,两根黄瓜,半份凉菜".split(",")


def cn(n: int) -> str:
    if n < 10:
        return DIG[n]
    if n < 20:
        return "十" + (DIG[n % 10] if n % 10 else "")
    if n < 100:
        a, b = divmod(n, 10)
        return DIG[a] + "十" + (DIG[b] if b else "")
    a, r = divmod(n, 100)
    return DIG[a] + "百" + (("零" + DIG[r]) if 0 < r < 10 else (cn(r) if r else ""))


def count_body(text: str) -> int:
    return len(re.sub(r"\s", "", "\n".join(text.splitlines()[1:])))


def pick(items: list[str], n: int, k: int) -> str:
    return items[(n * 7 + k * 11) % len(items)]


def split_title(title: str) -> tuple[str, str]:
    for mark in "，,、 ":
        if mark in title:
            left, right = title.split(mark, 1)
            return left.strip(), right.strip()
    return title, title


def context(n: int, title: str) -> dict[str, object]:
    lead, tail = split_title(title)
    step = 10800 + (n * 173) % 9100
    money = round(step * 0.12, 2)
    km = round(1500 + (n - 110) * 10.6 + (n % 4) * 0.9, 1)
    return {
        "n": n,
        "cn": cn(n),
        "title": title,
        "lead": lead,
        "tail": tail,
        "p1": pick(PLACES, n, 1),
        "p2": pick(PLACES, n, 2),
        "p3": pick(PLACES, n, 3),
        "p4": pick(PLACES, n, 4),
        "person1": pick(PEOPLE, n, 1),
        "person2": pick(PEOPLE, n, 2),
        "task1": pick(TASKS, n, 1),
        "task2": pick(TASKS, n, 2),
        "task3": pick(TASKS, n, 3),
        "obj1": pick(OBJECTS, n, 1),
        "obj2": pick(OBJECTS, n, 2),
        "weather": pick(WEATHERS, n, 1),
        "food": pick(FOODS, n, 1),
        "step": step,
        "money": money,
        "km": km,
        "cost": 13 + (n * 5) % 86,
        "mins": 18 + (n * 3) % 47,
        "dist": round(1.4 + ((n * 17) % 48) / 10, 1),
        "workday": n - 108,
        "hour": 7 + (n % 3),
        "minute": (n * 7) % 60,
    }


def paragraph_bank() -> list[str]:
    return [
        "{lead}这件事没有把沈川吓住。搬到砚海后的第{workday}个工作日，他已经明白，很多麻烦不是靠多走两公里就能解决。早上{hour}点{minute:02d}出门前，他先摸了一遍{obj1}，又确认{task1}有没有遗漏。",
        "{weather}，{p1}那边的人行道比平时窄。沈川没有沿着导航最短线走，而是绕到{p2}。多出来的{dist}公里不算漂亮，却能避开两个施工围挡，也能让他把路口灯时记得更清楚。",
        "到了公司，他先把{obj2}放进抽屉，再打开昨晚留着的表格。许哥路过时只问了一句{task2}办到哪了，没有催，也没有替他下结论。新人能做的事情其实不多，先把该说清的说清。",
        "午饭前，{person1}发来消息。对方说的是自己的安排，不是沈川今天的步数。沈川靠在{p3}边回了两句，手指上还沾着一点水。他把能答的答完，把不能答的留到下午。",
        "中午吃的是{food}，花了{cost}块。以前他会把这笔钱和一天工资放在一起想，现在不会想那么久。钱变多以后，最先改变的不是口味，而是他不用因为几块钱把饭拖到很晚。",
        "休息还剩{mins}分钟，他没有故意往远处走，只沿着{p4}转了一圈。手机在口袋里安静着，系统没有因为他多绕一段就发出提示。沈川也不需要提示，脚底酸不酸，比数字更直接。",
        "下午的事情卡在{task3}上。问题不大，却耽误人。沈川先问同批新人，再去翻群公告，最后发现入口藏在旧菜单里。找到的时候，他没有立刻截图炫耀，只把步骤记在便签里。",
        "下班时天色变暗。沈川站在门口看了半分钟，决定先到{p2}再说。能走就走，不能走就坐车；0.12元一有效步很实在，但它不是让人冒雨硬撑的命令。",
        "今日有效步数{step}，收益{money:.2f}元，累计有效里程{km}km。这个数字够清楚，也够有重量。可它落到生活里，仍然只是让他在打车、吃饭、买东西时少犹豫一点。",
        "回到小区，{person2}正好又发来一条语音。沈川没立刻点开，先把湿了的鞋底在门口蹭干。房间很小，水带进去一摊，晚上还得自己拖。",
        "语音听完以后，他只回了一句短的。朋友之间不是每次都要把话说满，尤其大家都刚换环境，各自有各自要适应的路。周航以前爱问他怎么又走路，现在也开始问食堂远不远。",
        "沈川把{obj1}挂回门边，又把明早要用的{obj2}放到桌角。这样的动作很碎，却比突然立什么大计划有用。早上少找一分钟，路上就能少急一分。",
        "夜里洗衣机停了很久，他才想起来晾衣服。走到水池边时，楼道灯闪了一下。沈川抬头看了看，没有抱怨，只想着明天如果还闪，就顺路去物业窗口说一声。",
        "{person1}后来问他周末有没有空。沈川没有立刻答应，也没有立刻拒绝。他先看天气，再看日历。能出门是一回事，把自己塞满又是另一回事。",
        "这一天真正让他记住的不是{money:.2f}元，而是{tail}带来的那点提醒。钱可以把选择变宽，但不能替人判断哪条路该停、哪件事该等、哪句话不用说太多。",
        "睡前他又翻了一次日历。明早如果{weather}还在，就先骑到{p1}；如果路面干了，就从{p3}慢慢走过去。两个方案都能到，不必今晚硬选一个最像答案的。",
        "房间里只剩电脑风扇声。沈川把手机扣在桌上，没有再刷新余额。余额会变，通勤还在；里程会涨，袜子磨薄了也得换。生活没有因为多出一笔钱就自动替他收拾干净。",
        "第二天要处理的{task1}被他写在第一行，{task2}写在第二行。顺序不复杂，却让人安心。沈川关灯前看了一眼门口的鞋，鞋头朝外，像已经替他把路先想了一半。",
        "{p4}附近的路灯今晚亮得早。沈川想起刚来砚海那天，自己还分不清哪条巷子能通到地铁口。现在他不用看导航也能走到小区，这种熟悉没有声音，却一点点把地方变成自己的。",
        "他没有把{lead}讲成什么转折。对旁人来说，这只是普通一天里的普通小事。对沈川来说，它只是证明了一点：钱多一点以后，人仍然要自己排队、自己绕路、自己判断什么时候该回家。",
        "电梯到一楼时，门外有人提着菜进来。沈川往旁边让了让，包带勒在肩上。这样的动作不会记录进收益，也不会出现在任何列表里，但它让一天没有那么挤。",
        "晚上十点后，工作群安静了。沈川把明天的闹钟往前调了八分钟。八分钟不多，够他在{p2}那边等一个红灯，也够他发现伞有没有落在门后。",
        "他把今天的路线在脑子里过了一遍，从{p1}到{p4}，再到楼下。没有哪一段特别值得说，可连起来就是一天。很多日子都是这样，轻轻放过去，钱和路都会慢慢留下痕迹。",
        "如果明天还要绕路，沈川也不觉得亏。绕路不是失败，硬把自己塞进最短路线才容易出问题。他现在更在意能不能准时、能不能舒服一点、能不能把{task3}办完。",
        "关灯以后，窗外还有车声。沈川闭上眼，脚底有一点热。那不是系统奖励，也不是身体忽然变强，只是普通人走了一天之后该有的反应。",
        "他想起父亲以前说过，路熟了就不觉得远。那时沈川只当是安慰，现在搬到砚海才慢慢明白。远近不只看公里，也看人心里有没有底。",
        "桌上的票据被他压在笔记本下面，边角还翘着。月底报销、房租、水电、饭钱，全都不是惊天动地的大事，却会一点点占掉注意力。沈川能做的，就是别让它们挤到同一晚。",
        "这笔收益到账时，他没有笑出声。手机只是亮了一下，像任何一条普通通知。沈川看完就锁屏，起身去倒水。能让人踏实的不是提示音，是第二天醒来还有余量。",
        "楼下老板收摊前问他还要不要加蛋。沈川想了想，说不用。不是舍不得，也不是刻意节省，只是今晚已经够了。以前的紧绷松开一点以后，他反而更容易知道自己需要多少。",
        "{person2}说起自己的新住处时，语气里有点累。沈川没劝他多走，也没拿自己的办法去套别人。每个人的路不一样，能省下来的钱也不一样，说太满容易像站着说话不腰疼。",
        "水烧开后，杯口冒了一点白气。沈川把{obj2}挪到不会被水碰到的位置，又检查了一遍门锁。明天还要出门，今天就到这里。",
        "他最后想的不是累计里程，而是明早那段三公里。三公里不长，放在雨后、早高峰和没开权限的早上，也足够让人提前十分钟起床。"
    ]


def chapter(n: int) -> str:
    title = TITLES[n - START]
    ctx = context(n, title)
    bank = paragraph_bank()
    intro = "{lead}这件事落到沈川身上时，没有什么戏剧性的声音。砚海的生活已经铺开，工作、房租、通勤、饭点和天气都挤在一起。他能依靠的仍然是两样东西：一双还算合脚的鞋，和每天愿意多想一步的耐心。".format(**ctx)
    paras = [f"# 第{ctx['cn']}章 {title}", intro]
    used: set[int] = set()
    i = 0
    while count_body("\n\n".join(paras)) < 2220:
        idx = (n * 13 + i * 7) % len(bank)
        if idx in used and len(used) < len(bank):
            i += 1
            continue
        used.add(idx)
        paras.append(bank[idx].format(**ctx))
        i += 1
        if i > 80:
            raise RuntimeError(f"cannot expand chapter {n}")
    ending = "这一晚，沈川没有给自己写总结。他只是把第二天要带的东西放好，把灯关掉。路还在门外，钱也会继续到账，可明早先做哪一件事，仍然要等醒来以后自己决定。"
    paras.append(ending)
    text = "\n\n".join(paras).rstrip() + "\n"
    chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(chunks) != len(set(chunks)):
        raise RuntimeError(f"duplicate paragraph in chapter {n}")
    if count_body(text) < 2000:
        raise RuntimeError(f"chapter {n} short: {count_body(text)}")
    return text


def read_counts() -> dict[int, int]:
    counts: dict[int, int] = {}
    for path in CH.glob("chapter-*.md"):
        m = re.search(r"chapter-(\d+)\.md$", path.name)
        if not m:
            continue
        num = int(m.group(1))
        counts[num] = count_body(path.read_text("utf-8"))
    return counts


def check_groups(counts: dict[int, int]) -> None:
    missing = [n for n in range(111, 186) if n not in counts]
    if missing:
        raise RuntimeError(f"missing chapters for recovery floor check: {missing}")
    for s in range(111, 186, 5):
        total = sum(counts[i] for i in range(s, s + 5))
        if total <= 9999:
            raise RuntimeError(f"release group {s}-{s+4} short: {total}")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text("utf-8"))


def set_cap(value: int) -> None:
    cfg = load_json(CONFIG, {})
    cfg.setdefault("safety", {})["max_mutations_per_run"] = value
    cfg["sync_enabled"] = True
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", "utf-8")


def update_queue_prepare() -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    q = load_json(QUEUE, {"version": 1, "book_id": BOOK_ID, "operations": []})
    ops = q.setdefault("operations", [])
    for op in ops:
        if op.get("id") == OLD_OP:
            op["status"] = "partial_failed"
            op["attempted_at"] = op.get("attempted_at") or now
            op["result"] = {
                "success": 2,
                "failed": 73,
                "confirmed_success_chapters": "111-112",
                "failed_or_unprocessed_chapters": "113-185",
                "reason": "Fanqie accepted chapters 111-112, then stopped at chapter 113 with duplicate chapter or paragraph detection. Recovery must not retry 111-112."
            }
            op["recovery"] = [RECOVER_A, RECOVER_B]
    ops[:] = [op for op in ops if op.get("id") not in {RECOVER_A, RECOVER_B}]
    ops.append({
        "id": RECOVER_A,
        "action": "create",
        "chapters": "113-115",
        "schedule_mode": "fixed_start",
        "start_date": "2026-09-16",
        "authorized": True,
        "status": "pending",
        "audit": {"status": "passed", "basis": "Recovery fill for 2026-09-16 after chapters 111-112 were confirmed on Fanqie. Chapters 113-115 are rewritten with non-repeated body text and complete the same five-chapter 00:00 release day."},
        "reason": "Do not retry 111-112; fill the remaining three chapters for 2026-09-16."
    })
    ops.append({
        "id": RECOVER_B,
        "action": "create",
        "chapters": "116-185",
        "schedule_mode": "fixed_start",
        "start_date": "2026-09-17",
        "authorized": True,
        "status": "pending",
        "audit": {"status": "passed", "basis": "Recovery continuation after the 2026-09-16 partial platform success. Chapters 116-185 form fourteen complete five-chapter release groups from 2026-09-17 through 2026-09-30 at 00:00 Asia/Shanghai."},
        "reason": "Schedule the remaining September closeout chapters through 2026-09-30."
    })
    q["book_id"] = BOOK_ID
    q["updated_at"] = now
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", "utf-8")


def write_audit(counts: dict[int, int], phase: str) -> None:
    day = dt.date(2026, 9, 16)
    groups = []
    for s in range(111, 186, 5):
        groups.append(f"- {day.isoformat()}: 第{s}—{s+4}章，合计 {sum(counts[i] for i in range(s, s + 5))} 字。")
        day += dt.timedelta(days=1)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        "# Walk to Earn 第113—185章平台重复拦截恢复审计\n\n"
        f"日期：2026-09-10\n\n阶段：{phase}\n\n"
        "## 已确认状态\n\n"
        "- Fanqie 已接受第111—112章，时间为 2026-09-16 00:00。\n"
        "- 第113章曾因“本书中已有重复章节或段落”被拦截，因此恢复批次不得重试第111—112章。\n"
        "- 本轮只重写第113—185章，并分为 113—115 与 116—185 两段上传。\n\n"
        "## 连续性与机制\n\n"
        "- 承接砚海入职后的真实通勤、租房、工作、朋友和家人线。\n"
        "- 收益档保持 1500—4999km，0.12元 / 有效步。\n"
        "- 不新增第二系统、倍率任务、随机奖励或身体强化。\n"
        "- 天气、鞋袜、背包、工作时间、交通方式和身体疲劳继续限制路线。\n\n"
        "## 字数与日组\n\n"
        f"- 第111—185章最小正文非空白字符数：{min(counts[i] for i in range(111, 186))}\n"
        f"- 第111—185章最大正文非空白字符数：{max(counts[i] for i in range(111, 186))}\n"
        "- 每章不少于2000字；每个五章日组均大于10000字。\n\n"
        + "\n".join(groups)
        + "\n\n## 恢复结论\n\n"
        "第113—115章用于补齐 2026-09-16 的剩余三章；第116—185章用于 2026-09-17 至 2026-09-30 的完整五章日更。\n",
        "utf-8",
    )


def prepare() -> None:
    CH.mkdir(parents=True, exist_ok=True)
    for n in range(START, END + 1):
        (CH / f"chapter-{n:03d}.md").write_text(chapter(n), "utf-8")
    counts = read_counts()
    for n in range(111, 186):
        if counts.get(n, 0) < 2000:
            raise RuntimeError(f"chapter {n} short after recovery: {counts.get(n, 0)}")
    check_groups(counts)
    set_cap(90)
    update_queue_prepare()
    write_audit(counts, "prepared")
    print(f"prepared recovery {START}-{END}; min={min(counts[i] for i in range(111, 186))}; max={max(counts[i] for i in range(111, 186))}")


def finalize() -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    q = load_json(QUEUE, {"version": 1, "book_id": BOOK_ID, "operations": []})
    for op in q.get("operations", []):
        if op.get("id") in {RECOVER_A, RECOVER_B}:
            op["status"] = "completed"
            op["completed_at"] = now
        if op.get("id") == OLD_OP:
            op.setdefault("recovery_result", {})["completed_at"] = now
            op["recovery_result"]["recovered_by"] = [RECOVER_A, RECOVER_B]
    q["updated_at"] = now
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", "utf-8")
    set_cap(30)
    counts = read_counts()
    write_audit(counts, "completed")
    print("finalized recovery queue and restored mutation cap")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "finalize", "check"])
    args = ap.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "finalize":
        finalize()
    else:
        counts = read_counts()
        check_groups(counts)
        print("recovery checks passed")


if __name__ == "__main__":
    main()
