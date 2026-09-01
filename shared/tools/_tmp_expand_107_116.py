from pathlib import Path


def insert(path: str, anchor: str, addition: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if anchor not in text:
        raise SystemExit(f'anchor missing in {path}: {anchor[:80]}')
    if addition.strip() in text:
        raise SystemExit(f'addition already present in {path}')
    p.write_text(text.replace(anchor, addition.rstrip() + '\n\n' + anchor, 1), encoding='utf-8')


def replace(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'replacement missing in {path}: {old}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


insert(
    'novels/endless-rail/chapters/volume-03/chapter-108.md',
    '晚上七点，白栎两箱敷料还躺在旧港覆盖货位里。',
    '''天完全黑下来以前，马立平又去K-17走了一遍。

滑床板边缘没有重新积冰。

他把白天刮下来的旧脂和擦拭布一起带回工务间，没有留在轨旁。赵琴在放行本上看到他回来，只问：“明早还按五点四十？”

“按。”

今天补涂通过，不代表明早最低温以后可以省掉第一遍检查。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-110.md',
    '下午两点，韩序从麦丘发来一张成品库照片。',
    '''沉泉把三个箱收回以后，炉坪F-03的临时占位也彻底结束。

赵琴下午查货位时，看见那张昨天写着S-31、S-32、S-33的小纸条还夹在板边，顺手抽出来扔进废纸筐。

电子记录已经有出站时间，现场牌子留着只会让下一班误以为位置还被占着。

孙晓雨后来看到货位照片，也没有要求炉坪把旧纸条留作“证明”。

货走了，位置就重新给下一批实际东西用。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-111.md',
    '五点半，炉坪外面的细冰粒停了。',
    '''晚饭前，许成把白天换下来的旧灯端子丢进废电气件盒。

孙海峰正好来找干布，看见以后拿起来捏了两下。

“还能留吗？”

“接触面已经松了。”

他又放回去。

维修区今天处理掉的东西不多，一只旧端子、一点脏润滑脂、几块湿布。没有哪件值得单独记成成果。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-112.md',
    '傍晚，炉坪覆盖区的三十六箱还在原位。',
    '''天黑以后，炉坪值守给覆盖区加了一次巡查。

最靠外的一组货封膜被冷风吹得轻轻响，绑带没有松。值守把旁边一块原本压防潮布的旧铁块挪远了一点，免得有人夜里经过绊脚。

三十六箱没有温控要求，现场也没给它们额外接电。

第二天白03来装以前，只需要保持干燥、封签完整和通道不被占。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-113.md',
    '下午一点半，白03驾驶员开始做出车前检查。',
    '''透明板挂回归途站以后，孙晓雨又拿一张空白候选单试填了一遍。

她故意只写“普通零件一箱”，不填货名，看五栏能不能判断出任何东西。

结果当然不能。

没有时限、后果、替代方案和去向，一箱零件只是一个物件，不足以进入承诺队列。

她把那张测试纸揉掉，候选页继续只保留真实任务。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-114.md',
    '三点三十八，F-03开始装货。',
    '''装货开始前，驾驶员把车内暖风关小了一档。

白03一会儿要连续开门，暖风开得再大也只会往站台跑。等六组货固定完，他才重新把驾驶位温度调回来。

孙海峰站在车外等最后一次箱号确认，鼻尖已经冻得发红，没因此催孙晓雨少扫一组。'''
)

insert(
    'novels/endless-rail/chapters/volume-03/chapter-115.md',
    '晚上七点零四，K-17货运放行恢复。',
    '''恢复放行以后，赵琴先把下午被压住的两项任务重新看了一遍。

那辆超过六吨的普通货车改到第二天早班，没有因为主路重新开放就夜里补跑。另一辆轻车本来就没有时限，也保持原来的明早计划。

K-17修好解决的是“现在能不能通”，没有把白天失去的所有窗口强行追回来。

炉坪夜班仍按正常人数值守，马立平只在交班时多留了一句：明早低温开闭继续看加热段。'''
)

replace(
    'novels/endless-rail/chapters/volume-03/chapter-112.md',
    '中间这段等待本身就是货物当前的真实位置。',
    '孙晓雨把当前位置保留为【炉坪F-03覆盖区 / 等待白03】。',
)
replace(
    'novels/endless-rail/chapters/volume-03/chapter-116.md',
    '几项改动都在变得好用，但第116章结束前，没有谁把它们打包宣布成一套成熟方案。',
    '几项改动都在变得好用，但眼下没有谁把它们打包宣布成一套成熟方案。',
)
replace(
    'novels/endless-rail/chapters/volume-02/chapter-046.md',
    '每次发送，机械实迹记录器都会留下真正的“发送动作”。',
    '每次发送，机械实迹记录器都会留下对应的发送痕迹。',
)
replace(
    'novels/endless-rail/chapters/volume-02/chapter-046.md',
    '这大概算暖桥第一次真正的邀请。',
    '这大概算暖桥第一次明确邀请归途站以后来看看。',
)
