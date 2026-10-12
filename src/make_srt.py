"""Write sidecar subtitle files (EN + 简体中文) matching the burned-in captions (src/timeline.py)."""
from common import OUTPUT
import timeline as TL

ZH = {
    "A ribbon of smoke.": "一缕轻烟。",
    "Smooth at first…": "起初，平滑如丝……",
    "…then, suddenly, chaos.": "……然后，骤然混沌。",
    "So we let a computer solve them — piece by piece.": "于是，我们让计算机来求解——一块一块地算。",
    "Divide space into millions of tiny cells.": "第一步：把空间划分成数百万个微小单元。",
    "In every cell, keep the balance:": "第二步：在每个单元里守恒：",
    "EQ_BALANCE": "流入 − 流出 = 变化",
    "March forward in time — thousands of steps.": "第三步：在时间上一步步推进——成千上万步。",
    "From simple local rules, the whole flow emerges.": "从简单的局部规则中，整个流动浮现出来。",
    "Finer cells reveal more — at a higher cost.": "网格越细，细节越多——代价也越高。",
    "The hardest part: turbulence.": "最难的部分：湍流。",
    "Swirls within swirls — from kilometres down to millimetres.": "涡中有涡——从千米到毫米。",
    "Too many to compute them all — so the smallest are modelled.": "涡太多，无法全部计算——于是最小的涡用模型来描述。",
    "Wings that lift us": "托起我们的机翼",
    "Cars that slip through the air": "穿风而过的汽车",
    "Turbines standing in the sea": "屹立海上的风机",
    "Tomorrow’s weather": "明天的天气",
    "The blood in our veins": "我们血管中的血液",
}
EXTRA = [  # equation beat inside S03 and the titles (baked into frames, listed here for subtitles)
    (TL.b(6) + 0.3, TL.b(6) + 3.2, "Air, water, blood — every fluid obeys the same rules.", "空气、水、血液——所有流体都遵循同样的规则。"),
    (TL.b(6) + 5.2, TL.b(6) + 8.2, "Newton’s F = ma, for every drop of fluid", "牛顿的 F = ma，作用于每一滴流体"),
    (TL.b(6) + 16.8, TL.b(6) + 19.4, "Beautiful — but almost impossible to solve by hand.", "优美——却几乎无法用手算求解。"),
    (TL.b(6) + 19.4, TL.b(6) + 22.6, "Even proving that smooth solutions always exist is an open $1,000,000 Millennium Prize problem.",
     "甚至连「光滑解是否总存在」都尚未被证明——这是悬赏一百万美元的千禧年大奖难题。"),
    (TL.TITLE[0], TL.TITLE[1], "SEEING THE INVISIBLE — an introduction to Computational Fluid Dynamics", "看见无形——计算流体力学入门"),
    (TL.END_TITLE[0], TL.END_TITLE[1], "Computational Fluid Dynamics — seeing the invisible, before it is built", "计算流体力学——在建造之前，看见无形"),
]


def ts(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


def main():
    items = []
    for (t0, t1, text, style, label) in TL.CAPTIONS:
        en = "what flows in − what flows out = what changes" if text == "EQ_BALANCE" else text
        items.append((t0, t1, en, ZH[text]))
    items += [(a, b, en, zh) for a, b, en, zh in EXTRA]
    items.sort()
    OUTPUT.mkdir(exist_ok=True)
    for lang, idx in (("en", 2), ("zh", 3)):
        with open(OUTPUT / f"Seeing_the_Invisible_CFD.{lang}.srt", "w", encoding="utf-8") as f:
            for k, it in enumerate(items, 1):
                f.write(f"{k}\n{ts(it[0])} --> {ts(it[1])}\n{it[idx]}\n\n")
    print(len(items), "subtitles written")


if __name__ == "__main__":
    main()
