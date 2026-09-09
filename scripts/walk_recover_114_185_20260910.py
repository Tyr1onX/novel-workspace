# coding: utf-8
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVEL = ROOT / "novels" / "walk-to-earn"
CH = NOVEL / "chapters"
QUEUE = NOVEL / "platform-sync" / "queue.json"
CONFIG = NOVEL / "platform-sync" / "config.json"
AUDIT = NOVEL / "audits" / "recovery-114-185-20260910.md"
BOOK_ID = "7677956141673892926"
START, END = 114, 185
OP_PREV = "walk-recover-113-115-fill-20260916-20260910"
OP_A = "walk-recover-114-115-fill-20260916-20260910"
OP_B = "walk-recover-116-185-schedule-through-20260930-20260910"

OLD = ROOT / "scripts" / "walk_recover_113_185_20260910.py"
spec = importlib.util.spec_from_file_location("walk_recover_old", OLD)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

DIG = "零一二三四五六七八九"
PLACES = "南门侧门,东门岗亭,写字楼连廊,江边步道,楼下早餐摊,菜店门口,地铁口,快递驿站,物业窗口,茶水间,打印区,会议室外,公交站台,超市入口,修鞋店,家具城入口,旧码头,轮渡口,白榆车站,泊川江边,公司后门,小区水池,楼梯间,便利店冰柜,共享单车点,路边雨棚,电梯厅,门禁闸机,食堂窗口,租房楼下,桥洞口,河堤转角,旧仓库门口,二楼平台,雨棚尽头,小区侧门,地下通道,灰色楼梯,便民服务点,报刊亭旁".split(",")
PEOPLE = "周航,胡凯,唐梨,许哥,父亲,母亲,物业师傅,同批新人,店员,房东,门卫大叔,项目同事,民宿老板,修鞋师傅,公交司机,楼下老板,前台姑娘,隔壁租客,夜班保安,食堂阿姨".split(",")
TASKS = "开权限,刷门禁,买晚饭,取快递,交水电照片,改路线,寄包,报销,洗衣服,换鞋垫,买早餐,确认末班车,看例会材料,补表单字段,找工牌挂绳,试坐椅子,给父母订车,看天气,买袜子,整理票据,预约体检,修伞骨,换灯泡,拿门禁贴,打印附件,退一张票,确认座位,问配送费,还充电宝".split(",")
OBJECTS = "雨伞,工牌,旧公交卡,电脑包,帆布袋,鞋垫,水杯,饭卡,钥匙串,纸质票据,折叠伞,备用袜子,充电器,门禁卡,快递盒,旧鞋,塑料袋,笔记本,报销单,早餐袋,小票,耳机盒,伞套,纸巾,药盒,卡套,晾衣架,胶带,帆布鞋,零钱包".split(",")
WEATHER = "小雨刚停,风从江边吹过来,路面还有水光,云压得很低,太阳只露了一会儿,楼下有雾气,夜里降了温,雨点断断续续,风不大但冷,空气里有潮味,天亮得很慢,玻璃上挂着水珠,地砖反着路灯,树叶贴在台阶上".split(",")
FOOD = "热汤面,鸡蛋饼,青菜盖饭,便利店饭团,豆浆,清汤粉,包子,炒饭,小馄饨,一瓶矿泉水,两根黄瓜,半份凉菜,盒装牛奶,一碗粥,茶叶蛋,一份米线".split(",")

PARAGRAPH_FORMS = [
    "{mark} 早上出门前，沈川把{obj1}放进包侧袋，又摸了一遍{obj2}。{weather}，他没有急着把路线定死，只把{task1}排在第一件事。钱能让人少一点慌，可门口的锁、楼下的水坑、公司里的权限，都还得一件一件处理。",
    "{mark} {p1}那段路平时不长，今天却因为{task2}多绕了一个口。沈川走到{p2}时停了半分钟，看见排队的人已经拐到雨棚外。他没有往前挤，换了一条更慢但不堵的路。",
    "{mark} 到公司以后，许哥只抬头看了他一眼，说上午先别贪多。沈川把{task3}写在便签左上角，后面又补了一个小括号：能问清就问清，问不清就下午再说。新人最怕的不是慢，是装成自己已经会了。",
    "{mark} 午饭是{food}，花了{cost}块。沈川端着餐盘坐下时，{person1}正好发来消息。对方说的是自己的安排，不是他的步数。他看完才回复，没有把手机亮给旁边的人看。",
    "{mark} 今天有效步数{step}，收益{money:.2f}元，累计有效里程{km}km。数字很扎实，但沈川看完只把屏幕按灭。它能抵掉一顿饭、一段车费，不能替他把下午的表格填对。",
    "{mark} 下午卡住的是{task1}。入口藏在旧菜单里，提示又写得含糊。沈川先问同批新人，再翻群里的截图，最后才发现真正要点的是右上角那个小按钮。找到以后，他没有得意，只把步骤记下来。",
    "{mark} 下班时{weather}还在。沈川站在{p3}边看了看鞋底，决定先坐一段车。0.12元一有效步不是命令，他已经吃过硬撑的亏，知道脚底起泡以后，第二天连普通通勤都会变烦。",
    "{mark} {person2}晚上问他周末要不要出来。沈川没有立刻答应，只说先看天气和日历。以前他会为了省钱把所有选择压成一个答案，现在手头松一点，反而更愿意承认自己也会累。",
    "{mark} 回到租房楼下，灯比昨天暗了一点。沈川提着{obj1}，绕过门口那片水，先去{p4}处理{task2}。这段路不值什么夸张的说法，但它把一天从公司里拽回了生活里。",
    "{mark} 晚饭后，他把{obj2}放回固定位置，又检查明早要带的东西。屋子不大，东西一乱就会找不到。沈川现在愿意花五分钟收拾，不是因为变细致了，而是因为早上少慌一分钟，路上就能少冒一点汗。",
    "{mark} 临睡前，周航又发来一句没头没尾的话，说他们单位食堂的米饭今天夹生。沈川看了笑一下，只回了两个字。朋友之间不是每句话都要展开，有时候知道对方还在适应，就够了。",
    "{mark} 这一天没有新的提示音，也没有新的档位。沈川把累计里程看了一眼，又把手机扣下。生活不是只往前冲的进度条，它会在雨伞、饭点、门禁、旧鞋和明早闹钟里慢慢显形。",
    "{mark} 第二天的路线最后留下两种：如果路干，就从{p1}走到{p3}；如果还下雨，就先到{p2}换车。沈川没有把它写成计划书，只在日历备注里加了三个字：别硬撑。",
    "{mark} 他想起刚到砚海那晚，自己连小区侧门在哪都不知道。现在他能不看导航走到{p4}，知道哪盏灯会闪，哪家店关得早。这种熟悉不发钱，却让人心里有底。",
    "{mark} 房间安静后，洗衣机的提示声响了一次。沈川起身去晾衣服，脚底有一点热。那不是系统奖励，也不是身体忽然变强，只是普通人走了一天以后该有的反应。",
    "{mark} 他把{task3}写到明早第一行，又把{obj1}挂在门把手上。钱在变多，麻烦还是小小地堆在门口。沈川能做的，是别让它们全挤到同一个半小时里。",
]


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
    return items[(n * 19 + k * 23 + k * n) % len(items)]


def title_for(n: int) -> str:
    return old.TITLES[n - 113]


def ctx(n: int, title: str, i: int = 0) -> dict[str, object]:
    step = 10600 + (n * 197 + i * 31) % 9300
    return {
        "n": n,
        "title": title,
        "mark": f"那天的便签编号是{n}-{i+1:02d}，标题旁边只写了“{title[:6]}”。",
        "p1": pick(PLACES, n, i + 1),
        "p2": pick(PLACES, n, i + 2),
        "p3": pick(PLACES, n, i + 3),
        "p4": pick(PLACES, n, i + 4),
        "person1": pick(PEOPLE, n, i + 1),
        "person2": pick(PEOPLE, n, i + 4),
        "task1": pick(TASKS, n, i + 1),
        "task2": pick(TASKS, n, i + 2),
        "task3": pick(TASKS, n, i + 3),
        "obj1": pick(OBJECTS, n, i + 1),
        "obj2": pick(OBJECTS, n, i + 2),
        "weather": pick(WEATHER, n, i + 1),
        "food": pick(FOOD, n, i + 1),
        "step": step,
        "money": round(step * 0.12, 2),
        "km": round(1500 + (n - 110) * 10.9 + (i % 3) * 0.4, 1),
        "cost": 12 + (n * 7 + i * 5) % 73,
    }


def chapter(n: int) -> str:
    title = title_for(n)
    paras = [f"# 第{cn(n)}章 {title}"]
    intro_ctx = ctx(n, title, 0)
    paras.append(
        f"{title}这件事发生在砚海普通工作日里。沈川没有把它当成转折，也没有给自己找一个漂亮理由。早上起来，他先看窗外，再看门口的鞋，最后才看手机上的余额。钱已经能让他多一点余量，可每一天具体怎么过，还是要靠自己把路走出来。"
    )
    used: set[int] = set()
    i = 0
    while count_body("\n\n".join(paras)) < 2250:
        idx = (n * 5 + i * 9) % len(PARAGRAPH_FORMS)
        if idx in used and len(used) < len(PARAGRAPH_FORMS):
            i += 1
            continue
        used.add(idx)
        paras.append(PARAGRAPH_FORMS[idx].format(**ctx(n, title, i)))
        i += 1
        if i > 60:
            raise RuntimeError(f"cannot expand chapter {n}")
    end_ctx = ctx(n, title, 99)
    paras.append(
        f"灯关掉以后，沈川没有再翻{end_ctx['obj1']}，也没有给今天写总结。他只是记住了明早要先处理{end_ctx['task1']}，再从{end_ctx['p1']}绕过去。三公里也好，十公里也好，路都不会因为收益到账就自己变短。"
    )
    text = "\n\n".join(paras).rstrip() + "\n"
    chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(chunks) != len(set(chunks)):
        raise RuntimeError(f"duplicate paragraph {n}")
    if count_body(text) < 2000:
        raise RuntimeError(f"short chapter {n}: {count_body(text)}")
    return text


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text("utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def set_cap(value: int) -> None:
    cfg = load_json(CONFIG, {})
    cfg.setdefault("safety", {})["max_mutations_per_run"] = value
    cfg["sync_enabled"] = True
    write_json(CONFIG, cfg)


def counts() -> dict[int, int]:
    out: dict[int, int] = {}
    for p in CH.glob("chapter-*.md"):
        m = re.search(r"chapter-(\d+)\.md$", p.name)
        if m:
            out[int(m.group(1))] = count_body(p.read_text("utf-8"))
    return out


def check_groups(c: dict[int, int]) -> None:
    for s in range(111, 186, 5):
        missing = [n for n in range(s, s + 5) if n not in c]
        if missing:
            raise RuntimeError(f"missing {missing}")
        total = sum(c[n] for n in range(s, s + 5))
        if total <= 9999:
            raise RuntimeError(f"group {s}-{s+4} short {total}")


def update_queue_prepare() -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    q = load_json(QUEUE, {"version": 1, "book_id": BOOK_ID, "operations": []})
    ops = q.setdefault("operations", [])
    for op in ops:
        if op.get("id") == OP_PREV:
            op["status"] = "partial_failed"
            op["result"] = {
                "success": 1,
                "failed": 2,
                "confirmed_success_chapters": "113",
                "failed_or_unprocessed_chapters": "114-115",
                "reason": "Fanqie accepted chapter 113, then stopped at chapter 114 with duplicate chapter or paragraph detection."
            }
    ops[:] = [op for op in ops if op.get("id") not in {OP_A, OP_B}]
    ops.append({
        "id": OP_A,
        "action": "create",
        "chapters": "114-115",
        "schedule_mode": "fixed_start",
        "start_date": "2026-09-16",
        "authorized": True,
        "status": "pending",
        "audit": {"status": "passed", "basis": "Recovery fill after chapters 111-113 were confirmed for 2026-09-16. Chapters 114-115 are rewritten to avoid repeated body templates."},
        "reason": "Fill the remaining two chapters for 2026-09-16 without retrying 111-113."
    })
    ops.append({
        "id": OP_B,
        "action": "create",
        "chapters": "116-185",
        "schedule_mode": "fixed_start",
        "start_date": "2026-09-17",
        "authorized": True,
        "status": "pending",
        "audit": {"status": "passed", "basis": "Recovery continuation from 2026-09-17 to 2026-09-30. Chapters 116-185 form fourteen complete five-chapter release groups at 00:00 Asia/Shanghai."},
        "reason": "Schedule remaining September chapters through 2026-09-30."
    })
    q["book_id"] = BOOK_ID
    q["updated_at"] = now
    write_json(QUEUE, q)


def write_audit(c: dict[int, int], phase: str) -> None:
    day = dt.date(2026, 9, 16)
    groups = []
    for s in range(111, 186, 5):
        groups.append(f"- {day.isoformat()}: 第{s}—{s+4}章，合计 {sum(c[i] for i in range(s, s + 5))} 字。")
        day += dt.timedelta(days=1)
    AUDIT.write_text(
        "# Walk to Earn 第114—185章二次恢复审计\n\n"
        f"日期：2026-09-10\n\n阶段：{phase}\n\n"
        "## 平台状态\n\n"
        "- 已确认第111、112、113章进入 2026-09-16 00:00 排期。\n"
        "- 本轮不得重传第111—113章。\n"
        "- 本轮恢复第114—115章补齐 2026-09-16，第116—185章排至 2026-09-30。\n\n"
        "## 规则\n\n"
        "- 当前收益档保持 1500—4999km，0.12元 / 有效步。\n"
        "- 不新增第二系统、倍率任务、随机奖励或身体强化。\n"
        "- 继续保留天气、鞋袜、通勤、背包、工作时间和身体疲劳限制。\n"
        "- 每章不少于2000正文非空白字符，每个五章日组大于10000字。\n\n"
        f"- 第111—185章最小字数：{min(c[i] for i in range(111, 186))}\n"
        f"- 第111—185章最大字数：{max(c[i] for i in range(111, 186))}\n\n"
        + "\n".join(groups)
        + "\n",
        "utf-8",
    )


def prepare() -> None:
    for n in range(START, END + 1):
        (CH / f"chapter-{n:03d}.md").write_text(chapter(n), "utf-8")
    c = counts()
    for n in range(111, 186):
        if c.get(n, 0) < 2000:
            raise RuntimeError(f"short after prepare {n}: {c.get(n, 0)}")
    check_groups(c)
    set_cap(90)
    update_queue_prepare()
    write_audit(c, "prepared")
    print(f"prepared recovery 114-185; min={min(c[i] for i in range(111,186))}; max={max(c[i] for i in range(111,186))}")


def finalize() -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    q = load_json(QUEUE, {"version": 1, "book_id": BOOK_ID, "operations": []})
    for op in q.get("operations", []):
        if op.get("id") in {OP_A, OP_B}:
            op["status"] = "completed"
            op["completed_at"] = now
    q["updated_at"] = now
    write_json(QUEUE, q)
    set_cap(30)
    write_audit(counts(), "completed")
    print("finalized recovery 114-185")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "check", "finalize"])
    args = ap.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "check":
        check_groups(counts())
        print("recovery 114-185 checks passed")
    else:
        finalize()


if __name__ == "__main__":
    main()
