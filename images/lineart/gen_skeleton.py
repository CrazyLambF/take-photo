#!/usr/bin/env python3
"""ST-01..ST-10 参数化姿势骨架生成器

路线 A（骨架 + AI 风格化）的第一段：按**姿势语义**手写 2D 关节点位，用 PIL 画成
工程线稿（stick figure），不依赖 MediaPipe / 照片提取（本机 mediapipe/cv2 不可用）。

坐标空间统一为 1080x1440（与封面 3:4 对齐），输出可任意放大：
  --w 1080  交付尺寸
  --w 1728  给 seedream 的 i2i 输入尺寸（3:4，总像素 3.98M，满足模型下限）

用法：
  python3 gen_skeleton.py                 # 全量 10 张，1080 交付版 + 1728 AI 输入版 + SVG
  python3 gen_skeleton.py --ids ST-01     # 指定
  python3 gen_skeleton.py --ai-only       # 只出 AI 输入版
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

W0, H0 = 1080, 1440  # 归一化坐标空间

FG = (0x3B, 0x36, 0x30)        # 深炭灰（与 lineart-ST01-skeleton.png 一致）
BG_WARM = (0xF6, 0xF0, 0xE5)   # 交付底：品牌奶油底
BG_WHITE = (0xFF, 0xFF, 0xFF)  # AI 输入底：纯白（§2.4 要求"白底、深灰线、实心关节点"）
GROUND_C = (0xC2, 0xBB, 0xAE)  # 地面线（浅，只做站位提示）

# ---- 姿势语义 -> 关节点位（x, y 直接写在 1080x1440 画布里） -------------------
# 关键：全部取"正面/3-4 侧/侧面"的统一投影，保证 10 张摆在一起像同一个人画的。
# face: 面部朝向角（0=朝右，90=朝下，180=朝左，270=朝上）；None=正对镜头不画朝向标记
POSES = {
    "ST-01": dict(
        name="自然直立", view="正面",
        # 双脚前后错开(丁字步)，重心放后腿，双手自然下垂并微微离开身体
        head=(545, 292, 58), neck=(545, 362), chest=(545, 520),
        sh=(455, 412, 630, 414), hip=(497, 700, 592, 700),
        elbow=(438, 622, 650, 618), wrist=(420, 838, 672, 830),
        knee=(490, 985, 600, 980), ankle=(498, 1292, 604, 1280),
        face=None, ground=1305,
    ),
    "ST-02": dict(
        name="45°侧身回眸", view="3/4 侧",
        # 身体侧转 45°，下巴微收，转头看镜头，一手轻拨头发
        head=(558, 296, 57), neck=(552, 366), chest=(548, 522),
        sh=(470, 418, 612, 406), hip=(505, 702, 576, 706),
        elbow=(446, 606, 664, 556), wrist=(430, 796, 618, 348),
        knee=(502, 986, 588, 982), ankle=(474, 1292, 636, 1298),
        face=196, ground=1305,
    ),
    "ST-03": dict(
        name="靠墙站", view="3/4 侧",
        # 肩或背轻靠墙，一腿屈膝脚掌点地，一手插袋
        head=(566, 292, 56), neck=(560, 362), chest=(556, 520),
        sh=(516, 420, 606, 414), hip=(528, 700, 584, 702),
        elbow=(500, 604, 630, 586), wrist=(494, 776, 582, 742),
        knee=(552, 984, 688, 946), ankle=(556, 1294, 640, 1286),
        face=178, ground=1300,
        wall=622,          # 背后墙面（竖线），表达"靠"
    ),
    "ST-04": dict(
        name="双手插袋", view="正面",
        # 拇指露在外其余入袋，肩膀放松下沉
        head=(543, 292, 58), neck=(543, 364), chest=(543, 524),
        sh=(450, 426, 638, 426), hip=(500, 700, 588, 700),
        elbow=(414, 618, 668, 616), wrist=(518, 764, 570, 762),
        knee=(492, 985, 596, 985), ankle=(478, 1295, 612, 1295),
        face=None, ground=1305,
    ),
    "ST-05": dict(
        name="松弛环抱", view="正面",
        # 双臂交叉但只抱一只手，避免紧绷；稍仰拍
        head=(545, 288, 58), neck=(545, 358), chest=(545, 516),
        sh=(452, 418, 634, 418), hip=(500, 700, 588, 700),
        elbow=(424, 636, 662, 640), wrist=(632, 516, 458, 528),
        knee=(495, 985, 592, 985), ankle=(483, 1293, 607, 1293),
        face=None, ground=1303,
    ),
    "ST-06": dict(
        name="拨发动态", view="正面",
        # 一手撩发，借风或甩动抓拍瞬间
        head=(548, 292, 57), neck=(548, 362), chest=(548, 520),
        sh=(454, 416, 634, 414), hip=(502, 702, 586, 702),
        elbow=(438, 620, 700, 520), wrist=(414, 830, 622, 350),
        knee=(498, 988, 590, 986), ankle=(487, 1294, 600, 1296),
        face=None, ground=1305,
    ),
    "ST-07": dict(
        name="提裙旋转", view="正面",
        # 双手提裙摆两侧向外，小幅度旋转；稍低机位
        head=(546, 290, 58), neck=(546, 360), chest=(546, 518),
        sh=(452, 418, 634, 418), hip=(500, 702, 588, 702),
        elbow=(404, 700, 682, 698), wrist=(352, 884, 734, 882),
        knee=(470, 980, 612, 990), ankle=(432, 1288, 668, 1290),
        face=None, ground=1300,
    ),
    "ST-08": dict(
        name="俏皮后勾腿", view="正面",
        # 重心放前腿，后腿小腿向后勾起
        head=(548, 288, 58), neck=(548, 358), chest=(548, 516),
        sh=(455, 415, 632, 415), hip=(500, 700, 585, 700),
        elbow=(432, 615, 658, 612), wrist=(420, 828, 676, 820),
        knee=(492, 985, 655, 950), ankle=(486, 1295, 742, 872),
        face=None, ground=1300,
    ),
    "ST-09": dict(
        name="踮脚伸展", view="近侧面",
        # 一手搭眉骨远眺，一臂上举；踮脚，表现身体舒展线条
        head=(556, 272, 56), neck=(552, 342), chest=(550, 500),
        sh=(524, 396, 598, 402), hip=(534, 690, 590, 696),
        elbow=(500, 470, 620, 300), wrist=(516, 318, 632, 196),
        knee=(548, 980, 562, 984), ankle=(548, 1266, 562, 1270),
        face=178, ground=1305,
        toe=True, toe_dir=-1,   # 踮脚：脚踝抬高、脚尖触地（朝左）
    ),
    "ST-10": dict(
        name="逆光剪影", view="正面",
        # 肢体夸张舒展：一臂远伸、一腿侧踢、不看镜头
        head=(548, 285, 58), neck=(548, 355), chest=(548, 512),
        sh=(452, 415, 636, 418), hip=(500, 700, 588, 700),
        elbow=(416, 600, 712, 368), wrist=(398, 806, 836, 286),
        knee=(492, 985, 668, 924), ankle=(484, 1294, 770, 1030),
        face=330, ground=1298,
    ),
}


def _s(v, S):
    return v * S


def draw_pose(p, W, H, bg, fg=FG, lw=15.0, clean=False):
    """在 WxH 画布上绘制骨架。lw 为 1080 空间下的主线宽。

    clean=True：只画人体骨架本体（白底、无地面线/无墙线/无标注），用于 AI 控制图。
    """
    S = W / W0
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    LW = lw * S
    JW = 9.0 * S            # 头部圈线宽
    JR = 11.0 * S           # 关节点半径
    GY = p.get("ground", 1305) * S

    def L(a, b, w=LW, col=fg):
        d.line([(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)], fill=col, width=max(1, round(w)))

    if not clean:
        # 地面线
        d.line([(170 * S, GY), (910 * S, GY)], fill=GROUND_C, width=max(1, round(4 * S)))
        # 支撑物（墙）
        if p.get("wall"):
            d.line([(p["wall"] * S, 520 * S), (p["wall"] * S, GY)], fill=GROUND_C,
                   width=max(1, round(6 * S)))

    hx, hy, hr = p["head"]
    shl, shr = (p["sh"][0], p["sh"][1]), (p["sh"][2], p["sh"][3])
    hl, hr_ = (p["hip"][0], p["hip"][1]), (p["hip"][2], p["hip"][3])
    el, er = (p["elbow"][0], p["elbow"][1]), (p["elbow"][2], p["elbow"][3])
    wl, wr = (p["wrist"][0], p["wrist"][1]), (p["wrist"][2], p["wrist"][3])
    kl, kr = (p["knee"][0], p["knee"][1]), (p["knee"][2], p["knee"][3])
    al, ar = (p["ankle"][0], p["ankle"][1]), (p["ankle"][2], p["ankle"][3])
    neck = (p["neck"][0], p["neck"][1])
    chest = (p["chest"][0], p["chest"][1])

    # 躯干：脊柱（颈-胸-胯中点）+ 锁骨 + 骨盆
    mid_hip = ((hl[0] + hr_[0]) / 2, (hl[1] + hr_[1]) / 2)
    L(neck, chest)
    L(chest, mid_hip)
    L(shl, shr)
    L(hl, hr_)
    L((hx, hy + hr * 0.95), neck)   # 颈

    # 四肢
    L(shl, el); L(el, wl)
    L(shr, er); L(er, wr)
    L(hl, kl); L(kl, al)
    L(hr_, kr); L(kr, ar)

    # 踮脚：脚尖补一小段（toe_dir=-1 表示朝左）
    if p.get("toe"):
        td = p.get("toe_dir", 1)
        L(al, (al[0] + 30 * td, al[1] + 30), w=LW * 0.7)
        L(ar, (ar[0] + 30 * td, ar[1] + 30), w=LW * 0.7)

    # 头
    d.ellipse([(hx - hr) * S, (hy - hr) * S, (hx + hr) * S, (hy + hr) * S],
              outline=fg, width=max(1, round(JW)))

    # 面部朝向标记（小鼻尖凸起），仅侧面/3-4 侧使用
    face = p.get("face")
    if face is not None:
        a = math.radians(face)
        bx, by = hx + math.cos(a) * (hr - 4), hy + math.sin(a) * (hr - 4)
        tx, ty = hx + math.cos(a) * (hr * 1.62), hy + math.sin(a) * (hr * 1.62)
        pang = math.radians(face + 62)
        bang = math.radians(face - 62)
        p1 = (hx + math.cos(pang) * hr * 0.92, hy + math.sin(pang) * hr * 0.92)
        p2 = (hx + math.cos(bang) * hr * 0.92, hy + math.sin(bang) * hr * 0.92)
        d.polygon([(p1[0] * S, p1[1] * S), (tx * S, ty * S), (p2[0] * S, p2[1] * S)], fill=fg)

    # 关节点（实心圆）
    for pt in (shl, shr, el, er, wl, wr, hl, hr_, kl, kr, al, ar):
        d.ellipse([(pt[0] - JR / S) * S, (pt[1] - JR / S) * S,
                   (pt[0] + JR / S) * S, (pt[1] + JR / S) * S], fill=fg)
    return img


def to_svg(p):
    """矢量版：单张 <1.5KB，可直接做标注层底图。"""
    hx, hy, hr = p["head"]
    shl, shr = (p["sh"][0], p["sh"][1]), (p["sh"][2], p["sh"][3])
    hl, hr_ = (p["hip"][0], p["hip"][1]), (p["hip"][2], p["hip"][3])
    el, er = (p["elbow"][0], p["elbow"][1]), (p["elbow"][2], p["elbow"][3])
    wl, wr = (p["wrist"][0], p["wrist"][1]), (p["wrist"][2], p["wrist"][3])
    kl, kr = (p["knee"][0], p["knee"][1]), (p["knee"][2], p["knee"][3])
    al, ar = (p["ankle"][0], p["ankle"][1]), (p["ankle"][2], p["ankle"][3])
    neck = (p["neck"][0], p["neck"][1])
    chest = (p["chest"][0], p["chest"][1])
    mid_hip = ((hl[0] + hr_[0]) / 2, (hl[1] + hr_[1]) / 2)

    def seg(a, b):
        return f"M{a[0]:.0f} {a[1]:.0f}L{b[0]:.0f} {b[1]:.0f}"

    main = " ".join(seg(*x) for x in [
        (shl, el), (el, wl), (shr, er), (er, wr),
        (hl, kl), (kl, al), (hr_, kr), (kr, ar),
    ])
    torso = " ".join(seg(*x) for x in [(neck, chest), (chest, mid_hip),
                                       (shl, shr), (hl, hr_),
                                       ((hx, hy + hr * 0.95), neck)])
    dots = " ".join(f"M{x:.0f} {y:.0f}h.1" for x, y in
                    (shl, shr, el, er, wl, wr, hl, hr_, kl, kr, al, ar))
    gy = p.get("ground", 1305)
    wall = (f'<path stroke="#C2BBAE" stroke-width="6" d="M{p["wall"]} 700L{p["wall"]} {gy}"/>'
            if p.get("wall") else "")
    c = "#%02X%02X%02X" % FG
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1440" role="img" '
        f'aria-label="{p["id"]} {p["name"]} 线稿示意"><title>{p["id"]} {p["name"]}</title>'
        f'<rect width="1080" height="1440" fill="#F6F0E5"/>'
        f'<path stroke="#C2BBAE" stroke-width="4" d="M170 {gy}L910 {gy}"/>{wall}'
        f'<g fill="none" stroke="{c}" stroke-linecap="round">'
        f'<path stroke-width="15" d="{main}"/><path stroke-width="15" d="{torso}"/></g>'
        f'<circle cx="{hx:.0f}" cy="{hy:.0f}" r="{hr:.0f}" fill="none" stroke="{c}" stroke-width="9"/>'
        f'<g fill="{c}" stroke="{c}" stroke-width="20" stroke-linecap="round"><path d="{dots}"/></g>'
        f'</svg>\n'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--ai-only", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ids = args.ids or list(POSES)
    rows = []
    for pid in ids:
        p = dict(POSES[pid]); p["id"] = pid

        # 1728x2304：seedream i2i 输入（纯白底、只留骨架本体，线更硬，便于模型识别为控制图）
        ai_img = draw_pose(p, 1728, 2304, BG_WHITE, clean=True)
        ai_path = out / f"_skeleton-ai-{pid}.png"
        ai_img.save(ai_path, "PNG", optimize=True)

        row = {"id": pid, "name": p["name"], "view": p["view"], "ai_input": ai_path.name,
               "ai_input_bytes": ai_path.stat().st_size}
        if not args.ai_only:
            img = draw_pose(p, 1080, 1440, BG_WARM)
            png = out / f"_skeleton-{pid}.png"
            img.save(png, "PNG", optimize=True)
            svg = out / f"_skeleton-{pid}.svg"
            svg.write_text(to_svg(p), encoding="utf-8")
            row.update(skeleton_png=png.name, skeleton_png_bytes=png.stat().st_size,
                       skeleton_svg=svg.name, skeleton_svg_bytes=svg.stat().st_size)
        rows.append(row)
        print(f"{pid} {p['name']:<8} ai={row['ai_input_bytes'] / 1024:.1f}KB "
              + (f"png={row['skeleton_png_bytes'] / 1024:.1f}KB "
                 f"svg={row['skeleton_svg_bytes']}B" if not args.ai_only else ""))

    (out / "_skeleton-index.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(rows)} 张骨架 → {out}")


if __name__ == "__main__":
    main()
