"""v2 sidecar subtitles (EN + 简体中文) from src/timeline_v2.py captions, plus the title sign and Clawd's bubbles.

  python make_srt_v2.py   -> output/Seeing_the_Invisible_CFD_v2.en.srt / .zh.srt
"""
import json

import timeline_v2 as TL
from common import OUTPUT, RENDERS

ZH = {
    "Air is invisible…": "空气是看不见的……",
    "…but it is never still.": "……但它从不静止。",
    "Smoke lets us see it move — for a moment.": "烟，让我们短暂地看见它的流动。",
    "an introduction to Computational Fluid Dynamics": "计算流体力学入门",
    "Wings, cars, turbines, storms, even our blood —": "机翼、汽车、风机、风暴，甚至我们的血液——",
    "all are shaped by flows we cannot see.": "都被我们看不见的流动所塑造。",
    "To design them, we must see the flow before it is built.": "要设计它们，就必须在建造之前看见流动。",
    "It does. Follow one tiny parcel of fluid…": "当然。跟随一小团流体……",
    "…and ask: what pushes it?": "……问一问：是什么在推动它？",
    "1 · PRESSURE": "1 · 压力",
    "Squeezed from high pressure towards low.": "从高压被挤向低压。",
    "2 · VISCOSITY": "2 · 黏性",
    "Neighbouring layers drag each other along.": "相邻的流层彼此拖拽。",
    "honey: a lot  ·  air: very little": "蜂蜜：很黏  ·  空气：几乎不黏",
    "3 · MOMENTUM": "3 · 动量",
    "Once moving, it keeps going —": "一旦动起来，就会继续前进——",
    "and the flow carries itself along.": "流动还会携带它自己前行。",
    "4 · CONSERVATION": "4 · 守恒",
    "Fluid never appears or vanishes:": "流体不会凭空出现或消失：",
    "narrow the path, and it speeds up.": "通道变窄，它就会加速。",
    "Together, they are the Navier–Stokes equations.": "合在一起，就是纳维–斯托克斯方程。",
    "Newton's “force = mass × acceleration” — for every drop of fluid.": "牛顿的「力 = 质量 × 加速度」——作用于每一滴流体。",
    "Easy to write. Almost impossible to solve.": "写下来很简单，解出来几乎不可能。",
    "proving they always behave is a $1,000,000 open problem": "证明它们始终「表现良好」，是悬赏一百万美元的未解难题",
    "A computer can't solve it everywhere at once…": "计算机无法一次解出所有地方……",
    "…so it works piece by piece.": "……所以它一块一块地算。",
    "STEP 1": "第一步",
    "Chop space into millions of tiny cells —": "把空间切成数百万个微小的单元——",
    "tiny where the action is, big where nothing happens.": "变化剧烈处切得细，平静处切得粗。",
    "STEP 2": "第二步",
    "In every cell, balance the books:": "在每个单元里记好账：",
    "what flows in  −  what flows out  =  what changes": "流入 − 流出 = 变化",
    "Each cell only talks to its neighbours.": "每个单元只和它的邻居交流。",
    "STEP 3": "第三步",
    "Take a tiny step forward in time…": "在时间上向前迈一小步……",
    "…then another. Tens of thousands of them.": "……再一步。几万步。",
    "Watch the swirls appear.": "看，涡旋出现了。",
    "Nobody told the computer to make swirls —": "没人告诉计算机要画出涡旋——",
    "they emerge from the rules.": "它们从规则中自然浮现。",
    "And nature agrees: real clouds behind an island.": "大自然也这样认为：海岛背后真实的云。",
    "Clouds behind Alejandro Selkirk Island, Chile · Landsat 7 image: NASA/GSFC": "智利亚历杭德罗·塞尔扣克岛后方的云 · Landsat 7 图像：NASA/GSFC",
    "More cells, sharper flow…": "单元越多，流动越清晰……",
    "…but halve the cell size in 3D, and the work grows 16×.": "……但在三维中单元尺寸减半，计算量就增加 16 倍。",
    "The real challenge: turbulence.": "真正的难题：湍流。",
    "Big swirls feed smaller swirls — down to fractions of a millimetre.": "大涡喂养小涡——一直小到不足一毫米。",
    "Far too many to compute them all.": "多到根本算不完。",
    "So the smallest swirls are modelled, not computed —": "所以最小的涡用模型来描述，而不是直接计算——",
    "a bit like choosing camera settings:": "有点像选择相机设置：",
    "AIRCRAFT|the swirl behind every wingtip": "飞机｜每个翼尖后的涡旋",
    "CARS|less drag, less fuel": "汽车｜更小阻力，更省油",
    "OFFSHORE WIND|turbines standing in the waves": "海上风电｜屹立浪中的风机",
    "WEATHER|tomorrow's winds, computed today": "天气｜明天的风，今天算出",
    "MEDICINE|blood flowing through an artery": "医学｜在动脉中流动的血液",
    "Computational Fluid Dynamics:": "计算流体力学：",
    "seeing the invisible — before it is built.": "在建造之前，看见无形。",
    "Simulations, renders and music: all made in code.|Lattice-Boltzmann flows on the GPU · Blender · a procedural score|with Clawd, the Claude Code critter":
        "模拟、渲染与音乐：全部由代码生成。｜GPU 上的格子玻尔兹曼流动 · Blender · 程序化配乐｜主演：Clawd（Claude Code 的小像素生物）",
}
BUBBLE_ZH = {"!?": "！？", "hi!": "嗨！", "why care?": "为什么要关心？", "does air follow rules?": "空气遵守规则吗？",
             "whoa!": "哇！", "sticky!": "好黏！", "it keeps going!": "它一直在前进！", "zoom!": "嗖！",
             "uh-oh": "糟了", "can a computer solve it?": "计算机能解吗？", "I'm made of cells too!": "我也是由单元组成的！",
             "that's me!": "那是我！", "phew!": "呼！", "why is it so hard?": "为什么这么难？", "wheee!": "呜呼！",
             "less drag!": "阻力更小！", "hello sea!": "你好，大海！", "storm ahead!": "前方有风暴！",
             "surf's up!": "冲浪咯！", "I can see it!": "我看见了！", "bye!": "再见！", "...": "……"}
EXTRA = [(10.1, 13.9, "SEEING THE INVISIBLE", "看见无形")]


def ts(sec):
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"


def main():
    items = []
    for b0, b1, style, text, ex in TL.CAPTIONS:
        if style in ("label",):
            continue
        en = text.replace("|", " — ")
        zh = ZH.get(text, en).replace("｜", " — ")
        items.append((b0 * 2.0, b1 * 2.0, en, zh))
    for b0, b1, en, zh in EXTRA:
        items.append((b0 * 2.0, b1 * 2.0, en, zh))
    for sid, b0, b1, *_ in TL.SHOTS:
        p = RENDERS / sid / "clawd_track.json"
        if not p.exists():
            continue
        for cf, kind in json.loads(p.read_text())["cues"]:
            if kind.startswith("say:"):
                _, dur, text = kind.split(":", 2)
                t0 = (b0 * TL.BAR + cf - 1) / TL.FPS
                items.append((t0, t0 + int(dur) / TL.FPS, f"[Clawd] {text}", f"[Clawd] {BUBBLE_ZH.get(text, text)}"))
    items.sort()
    for lang, k in (("en", 2), ("zh", 3)):
        lines = []
        for i, it in enumerate(items, 1):
            lines += [str(i), f"{ts(it[0])} --> {ts(it[1])}", it[k], ""]
        (OUTPUT / f"Seeing_the_Invisible_CFD_v2.{lang}.srt").write_text("\n".join(lines), encoding="utf-8")
    print("srt:", len(items), "entries")


if __name__ == "__main__":
    main()
