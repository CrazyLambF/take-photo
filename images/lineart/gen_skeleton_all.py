#!/usr/bin/env python3
"""全量矢量体块骨架：SIT/STREET/TRAVEL/HOME/CAFE/BACK/PROP/SCENE 各 10 条（80 张）

单一数据源 = 关节点位（FK 由角度算出）。同一套 joints 同时驱动：
  · images/lineart/skeleton/{ID}.svg / .png   1080x1440 交付骨架（奶油底 + 体块）
  · images/lineart/_ctl/{ID}.png              1728x2304 AI 控制图（白底 + 有体积人偶）
  · images/lineart/joints.json                ST-01..10 + 80 条 = 90 条的标注坐标契约

坐标空间 1080x1440（3:4）；写盘时归一化到 0..1。
L/R 一律按「画面左 / 画面右」。

用法：
  python3 gen_skeleton_all.py                 # 80 张全量
  python3 gen_skeleton_all.py --ids SIT-01    # 指定
  python3 gen_skeleton_all.py --contact       # 附带总览图
"""
import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_skeleton import POSES as ST_POSES  # noqa: E402

W0, H0 = 1080, 1440
C = 540.0                      # 画面中轴

# ---- 骨长（1080x1440 空间，与 ST-01..10 完全同一套比例） --------------------
R_HEAD = 57.0
L_NECK = 68.0                  # 头心 -> 颈点
L_SPINE = 340.0                # 颈点 -> 髋心
T_SHO = 50.0                   # 颈 -> 肩线
SH_HALF = 90.0                 # 肩半宽
HIP_HALF = 47.0                # 髋半宽
L_UARM, L_FARM = 210.0, 220.0
L_THIGH, L_SHIN = 285.0, 307.0
R_UARM, R_FARM = (21.0, 15.5), (15.5, 12.0)
R_THIGH, R_SHANK = (30.0, 23.0), (23.0, 15.0)
R_NECK, R_BALL = 22.0, 0.0

SK_BG = (0xF6, 0xF0, 0xE5)
SK_INK = (0x3B, 0x36, 0x30)
SK_BODY = (0xDD, 0xD4, 0xC4)
SK_SW = 4.0
CTL_BG = (0xFF, 0xFF, 0xFF)
CTL_INK = (0x2E, 0x29, 0x25)
CTL_BODY = (0x6E, 0x68, 0x60)
CTL_SW = 4.6


def mir(a):
    """在竖轴上镜像一组角度（画面左 <-> 画面右）。"""
    return (180.0 - a[0], 180.0 - a[1])


def d(a):
    r = math.radians(a)
    return math.cos(r), math.sin(r)


def add(p0, a, L):
    dx, dy = d(a)
    return (p0[0] + dx * L, p0[1] + dy * L)


# ---------------------------------------------------------------- FK -> 17 点
def build(s, sc=1.0):
    hip = s["hip"]
    sp, hd = s["spine"], s["head"]
    neck = add(hip, sp, L_SPINE * sc)
    chest = add(hip, sp, L_SPINE * 0.53 * sc)
    shm = add(neck, sp + 180, T_SHO * sc)
    perp = sp + 90
    ux, uy = d(perp)
    hw = SH_HALF * s.get("shw", 1.0) * sc
    shL = (shm[0] - ux * hw, shm[1] - uy * hw)
    shR = (shm[0] + ux * hw, shm[1] + uy * hw)
    hw2 = HIP_HALF * s.get("shw", 1.0) * sc
    hipL = (shm[0] - ux * hw2 + (hip[0] - shm[0]), shm[1] - uy * hw2 + (hip[1] - shm[1]))
    hipR = (shm[0] + ux * hw2 + (hip[0] - shm[0]), shm[1] + uy * hw2 + (hip[1] - shm[1]))
    # 髋点严格按 pelvis 中心 + 半宽
    cx, cy = hip
    hipL = (cx - ux * hw2, cy - uy * hw2)
    hipR = (cx + ux * hw2, cy + uy * hw2)

    J = dict(hip=hip, neck=neck, chest=chest, shL=shL, shR=shR, hipL=hipL, hipR=hipR)
    J["headCenter"] = add(neck, hd, L_NECK * sc)
    afs = s.get("afs", (1.0, 1.0))
    fs = s.get("fs", (1.0, 1.0))
    for k, a in (("L", s["armL"]), ("R", s["armR"])):
        sh = shL if k == "L" else shR
        el = add(sh, a[0], L_UARM * afs[0] * sc)
        J["elbow" + k] = el
        J["wrist" + k] = add(el, a[1], L_FARM * afs[1] * sc)
    for k, a in (("L", s["legL"]), ("R", s["legR"])):
        hp = hipL if k == "L" else hipR
        kn = add(hp, a[0], L_THIGH * fs[0] * sc)
        J["knee" + k] = kn
        J["ankle" + k] = add(kn, a[1], L_SHIN * fs[1] * sc)
    return J


# ---------------------------------------------------------------- 造型图元
def chair_shapes(J, ground, s):
    hx, hy = J["hip"]
    w = 150.0
    out = [
        ("poly", [(hx - w, hy + 6), (hx + w, hy + 6), (hx + w, hy + 46), (hx - w, hy + 46)], "chair"),
        ("poly", [(hx - w - 6, hy - 200), (hx - w + 34, hy - 200),
                  (hx - w + 34, hy + 10), (hx - w - 6, hy + 10)], "chair"),
        ("cap", (hx - w + 16, hy + 44, hx - w + 16, ground - 6, 9.0, 9.0), "chair"),
        ("cap", (hx + w - 16, hy + 44, hx + w - 16, ground - 6, 9.0, 9.0), "chair"),
    ]
    return out


def shapes(J, s, ground=None, sc=1.0):
    """返回 [(kind, payload, tone)]，tone: 'body' | 'far'。"""
    hx, hy = J["headCenter"]
    side = s["view"] in ("side",)
    rx, ry = R_HEAD * (0.95 if side else 0.84), R_HEAD * 1.03
    out = [("ell", ((hx, hy), rx, ry), "body"),
           ("cap", (J["headCenter"][0], J["headCenter"][1] + ry * 0.62,
                    (J["neck"][0] + J["chest"][0]) / 2, (J["neck"][1] + J["chest"][1]) / 2,
                    R_NECK, R_NECK * 0.9), "body")]

    # 胸廓 / 骨盆 / 腰：以肩线与髋线为外框的六边形体块
    shL, shR = J["shL"], J["shR"]
    hipL, hipR, ch = J["hipL"], J["hipR"], J["chest"]
    wL = 0.80 if side else 0.86
    waistL = ((shL[0] + hipL[0]) / 2 * wL + ch[0] * (1 - wL),
              (shL[1] + hipL[1]) / 2 * wL + ch[1] * (1 - wL))
    waistR = ((shR[0] + hipR[0]) / 2 * wL + ch[0] * (1 - wL),
              (shR[1] + hipR[1]) / 2 * wL + ch[1] * (1 - wL))
    out.append(("poly", [shL, shR, waistR, (hipR[0] + 0, hipR[1] - 6),
                         (hipL[0], hipL[1] - 6), waistL], "body"))
    ptop = (hipL[0] + (hipR[0] - hipL[0]) * 0.0, hipL[1] - 8)
    out.append(("poly", [(hipL[0], hipL[1] - 10), (hipR[0], hipR[1] - 10),
                         (hipR[0] - (hipR[0] - hipL[0]) * 0.06, hipR[1] + 58),
                         (hipL[0] + (hipR[0] - hipL[0]) * 0.06, hipL[1] + 58)],
                "body"))

    # 腿
    far_tone = "far" if s["view"] in ("side", "34") else "body"
    order = [("R", "far"), ("L", "body")] if s["view"] in ("side", "34") else [("L", "body"), ("R", "body")]
    legsh = []
    for k, tone in order:
        hp = J["hipL"] if k == "L" else J["hipR"]
        kn, an = J["knee" + k], J["ankle" + k]
        legsh.append(("cap", (hp[0], hp[1], kn[0], kn[1], *R_THIGH), tone))
        legsh.append(("cap", (kn[0], kn[1], an[0], an[1], *R_SHANK), tone))
        legsh.append(("circ", (kn, 17.5), tone))
        fd = s.get("foot_dir", (-1, 1))[0 if k == "L" else 1]
        legsh.append(("poly", _foot(an, fd, s, ground, sc), tone))
    out[:0] = legsh

    # 手：沿前臂方向的小椭球
    for k in ("L", "R"):
        el, wr = J["elbow" + k], J["wrist" + k]
        ang = math.degrees(math.atan2(wr[1] - el[1], wr[0] - el[0]))
        out.append(("cap", (wr[0], wr[1], *add(wr, ang, 22), 14.0, 10.5), "body"))

    # 手臂（压在躯干之上；侧视远侧先画）
    arms = []
    for k, tone in ([("R", "far"), ("L", "body")] if s["view"] == "side" else [("L", "body"), ("R", "body")]):
        sh = J["shL"] if k == "L" else J["shR"]
        el, wr = J["elbow" + k], J["wrist" + k]
        arms.append(("cap", (sh[0], sh[1], el[0], el[1], *R_UARM), tone))
        arms.append(("circ", (el, 16.5), tone))
        arms.append(("cap", (el[0], el[1], wr[0], wr[1], *R_FARM), tone))
        arms.append(("circ", (sh, 21.0), tone))
    out.extend(arms)
    if s.get("chair"):
        out = chair_shapes(J, ground, s) + out
    return out


def _foot(an, fd, s, ground=None, sc=1.0):
    x, y = an
    lifted = s.get("lifted", False)
    gy = ground or s.get("ground") or 1305
    if lifted or abs(y - gy) > 90:
        gy = y + 34
    toe = (x + fd * 46 * sc, gy - 6)
    heel = (x - fd * 12 * sc, gy - 7)
    return [(x + fd * 8, y - 15), toe, (toe[0] - fd * 4, toe[1] + 4), heel,
            (heel[0] + fd * 6, heel[1] - 8)]


def parts(sh_list):
    """把相邻同 tone 的图元合并成一个复合部件（一次描边，避免内部接缝）。"""
    grp, cur, cur_tone = [], [], None
    for kind, pl, tone in sh_list:
        if tone != cur_tone and cur:
            grp.append((cur_tone, cur))
            cur = []
        cur_tone = tone
        cur.append((kind, pl))
    if cur:
        grp.append((cur_tone, cur))
    return grp


def _draw_group(d, items, grow, col, W, K):
    for kind, pl in items:
        if kind == "ell":
            (cx, cy), rx, ry = pl
            d.ellipse([(cx - rx) * K - grow, (cy - ry) * K - grow,
                       (cx + rx) * K + grow, (cy + ry) * K + grow], fill=col)
        elif kind == "circ":
            (cx, cy), r = pl
            d.ellipse([cx * K - r * K - grow, cy * K - r * K - grow,
                       cx * K + r * K + grow, cy * K + r * K + grow], fill=col)
        elif kind == "cap":
            x0, y0, x1, y1, r0, r1 = pl
            p0 = (x0 * K, y0 * K)
            p1 = (x1 * K, y1 * K)
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            a0, b0 = r0 * K + grow, r1 * K + grow
            d.polygon([(p0[0] + nx * a0, p0[1] + ny * a0), (p1[0] + nx * b0, p1[1] + ny * b0),
                       (p1[0] - nx * b0, p1[1] - ny * b0), (p0[0] - nx * a0, p0[1] - ny * a0)],
                      fill=col)
            d.ellipse([p0[0] - a0, p0[1] - a0, p0[0] + a0, p0[1] + a0], fill=col)
            d.ellipse([p1[0] - b0, p1[1] - b0, p1[0] + b0, p1[1] + b0], fill=col)
        elif kind == "poly":
            pts = pl
            if grow:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                pts = [(p[0] + (p[0] - cx) / max(1e-6, math.hypot(p[0] - cx, p[1] - cy)) * grow / K,
                        p[1] + (p[1] - cy) / max(1e-6, math.hypot(p[0] - cx, p[1] - cy)) * grow / K)
                       for p in pts]
            d.polygon([(p[0] * K, p[1] * K) for p in pts], fill=col)


def render(sh_list, W, H, bg, ink, body, sw, ground=None, show_ground=False):
    K = W / W0
    img = Image.new("RGB", (W, H), bg)
    groups = parts(sh_list)
    for _pass in ("ink", "body"):
        for tone, items in groups:
            m = Image.new("L", (W, H), 0)
            dm = ImageDraw.Draw(m)
            _draw_group(dm, items, sw * K if _pass == "ink" else 0.0, 255, W, K)
            if tone == "chair":
                col = ink if _pass == "ink" else (0xD8, 0xD0, 0xC0)
            else:
                col = ink if _pass == "ink" else (body if tone == "body" else tuple(
                    int(v * 0.90) for v in body))
            img.paste(col, (0, 0), m)
    return img


def svg(sh_list, s, ground=None):
    K = 1.0
    hx, hy = 0, 0
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1440" role="img" '
           f'aria-label="{s["id"]} {s["name"]} 体块骨架"><title>{s["id"]} {s["name"]}</title>',
           '<rect width="1080" height="1440" fill="#F6F0E5"/>']
    if s.get("show_ground", True):
        gy = ground or 1305
        out.append(f'<path stroke="#C2BBAE" stroke-width="4" d="M170 {gy:.0f}L910 {gy:.0f}"/>')
    body_hex = "#%02X%02X%02X" % SK_BODY
    ink_hex = "#%02X%02X%02X" % SK_INK
    for tone, items in parts(sh_list):
        g = []
        for kind, pl in items:
            if kind == "ell":
                (cx, cy), rx, ry = pl
                g.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rx:.0f}" ry="{ry:.0f}"/>')
            elif kind == "circ":
                (cx, cy), r = pl
                g.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}"/>')
            elif kind == "cap":
                x0, y0, x1, y1, r0, r1 = pl
                dx, dy = x1 - x0, y1 - y0
                L = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / L, dx / L
                g.append(
                    f'<path d="M{x0 + nx * r0:.0f} {y0 + ny * r0:.0f}L{x1 + nx * r1:.0f} '
                    f'{y1 + ny * r1:.0f}A{r1:.0f} {r1:.0f} 0 0 1 {x1 - nx * r1:.0f} '
                    f'{y1 - ny * r1:.0f}L{x0 - nx * r0:.0f} {y0 - ny * r0:.0f}'
                    f'A{r0:.0f} {r0:.0f} 0 0 1 {x0 + nx * r0:.0f} {y0 + ny * r0:.0f}Z"/>')
            elif kind == "poly":
                g.append('<path d="M' + "L".join(f"{p[0]:.0f} {p[1]:.0f}" for p in pl) + 'Z"/>')
        out.append(f'<g fill="{body_hex}" stroke="{ink_hex}" stroke-width="{SK_SW}" '
                   f'stroke-linejoin="round">' + "".join(g) + "</g>")
    # 关节点
    return "\n".join(out) + "\n</svg>\n"


def contact(ids, out_path, cols=5, cell=(216, 288)):
    rows = (len(ids) + cols - 1) // cols
    W, H = cell[0] * cols, cell[1] * rows
    sheet = Image.new("RGB", (W, H), (250, 246, 238))
    d_ = ImageDraw.Draw(sheet)
    for i, pid in enumerate(ids):
        p = HERE / "skeleton" / f"{pid}.png"
        if not p.exists():
            continue
        im = Image.open(p).resize(cell, Image.LANCZOS)
        x, y = (i % cols) * cell[0], (i // cols) * cell[1]
        sheet.paste(im, (x, y))
        d_.text((x + 6, y + 4), pid, fill=(150, 90, 40))
    sheet.save(out_path, "PNG", optimize=True)
    return out_path


# ============================================================ 80 条姿势数据
# 角度制：0=画面右，90=画面下，180=画面左，270=画面上。
# armL=(上臂绝对角, 前臂绝对角)；legL=(大腿绝对角, 小腿绝对角)。
# L/R 均为「画面左 / 画面右」。
def P(pid, name, view, hip, spine=-90.0, head=None, armL=(98, 94), armR=None,
      legL=(90, 88), legR=(92, 90), face=None, ground=None, lifted=False,
      foot_dir=(-1, 1), show_ground=True, fs=(1.0, 1.0), afs=(1.0, 1.0)):
    return dict(id=pid, name=name, view=view, hip=hip, spine=spine,
                head=spine if head is None else head,
                armL=tuple(armL), armR=tuple(mir(armL) if armR is None else armR),
                legL=tuple(legL), legR=tuple(legR),
                face=face, ground=ground, lifted=lifted, fs=tuple(fs), afs=tuple(afs),
                foot_dir=foot_dir, show_ground=show_ground)


SPECS = {p["id"]: p for p in [
    # ---------------------------------------------------------------- SIT
    P("SIT-01", "前倾标准坐", "34", (545, 895), -86, armL=(102, -58), legL=(24, 92), legR=(32, 96), face=5),
    P("SIT-02", "侧坐叠腿", "side", (470, 880), -88, armL=(100, 20), armR=(112, 62),
      legL=(12, 114), legR=(22, 100), face=0, foot_dir=(1, 1)),
    P("SIT-03", "台阶交叉坐", "34", (505, 860), -85, -88, armL=(118, -10), armR=(95, 150),
      legL=(45, 66), legR=(20, 96), face=20),
    P("SIT-04", "草地盘坐", "front", (540, 1005), -92, armL=(108, 55),
      legL=(168, 8), legR=(12, 172)),
    P("SIT-05", "屈膝抱腿", "34", (540, 1045), -80, armL=(100, 160), armR=(80, 20),
      legL=(262, 72), legR=(279, 85), face=15),
    P("SIT-06", "沙发慵懒瘫", "side", (445, 900), -122, -108, armL=(100, 60), armR=(70, 20),
      legL=(2, -32), legR=(30, 74), face=0, foot_dir=(1, 1)),
    P("SIT-07", "后仰手撑", "34", (540, 1005), -116, -102, armL=(114, 84),
      legL=(30, 86), legR=(40, 78), face=5),
    P("SIT-08", "日式跪坐", "34", (540, 1115), -92, armL=(104, 58),
      legL=(72, 168), legR=(78, 172), face=25),
    P("SIT-09", "反坐椅背", "34", (540, 830), -94, armL=(108, -72),
      legL=(98, 96), legR=(94, 92), face=15),
    P("SIT-10", "车内托腮", "side", (500, 875), -84, -78, armL=(82, -76), armR=(86, 96),
      legL=(22, 94), legR=(30, 98), face=0, foot_dir=(1, 1)),
    # ------------------------------------------------------------- STREET
    P("STREET-01", "行走抓拍", "34", (540, 700), -90, armL=(112, 66), armR=(72, 120),
      legL=(108, 84), legR=(74, 92), face=20),
    P("STREET-02", "回眸瞬间", "34", (540, 705), -92, -95, armL=(98, 72), armR=(118, 262),
      legL=(100, 86), legR=(78, 88), face=205),
    P("STREET-03", "斑马线穿过", "front", (540, 700), -90, armL=(104, 86), armR=(76, 92),
      legL=(114, 96), legR=(66, 88)),
    P("STREET-04", "路边倚靠", "34", (540, 712), -94, armL=(115, 150), armR=(92, 158),
      legL=(94, 88), legR=(104, 54), face=25),
    P("STREET-05", "推门瞬间", "34", (540, 705), -88, armL=(100, 95), armR=(48, 8),
      legL=(92, 90), legR=(86, 86), face=10),
    P("STREET-06", "橱窗前走过", "34", (545, 700), -90, armL=(105, 88), armR=(74, 95),
      legL=(104, 88), legR=(76, 90), face=0),
    P("STREET-07", "倚车摆拍", "34", (530, 705), -92, armL=(116, 146), armR=(96, 100),
      legL=(96, 86), legR=(86, 94), face=15),
    P("STREET-08", "雨天打伞", "34", (540, 700), -90, armL=(238, 268), armR=(96, 92),
      legL=(98, 88), legR=(82, 86), face=20),
    P("STREET-09", "蹲姿互动", "34", (540, 975), -72, -85, armL=(95, 72), armR=(85, 110),
      legL=(20, 130), legR=(26, 124), face=30),
    P("STREET-10", "霓虹夜景", "34", (540, 700), -91, armL=(96, 92), armR=(272, 300),
      legL=(94, 88), legR=(88, 92), face=200),
    # ------------------------------------------------------------- TRAVEL
    P("TRAVEL-01", "错位借位", "front", (540, 700), -90, armL=(248, 258), armR=(292, 282),
      legL=(90, 88), legR=(92, 90)),
    P("TRAVEL-02", "人在景中", "back", (540, 700), -90, armL=(95, 92), legL=(90, 88), legR=(92, 90)),
    P("TRAVEL-03", "背影地标同框", "back", (540, 705), -90, armL=(156, 168), armR=(24, 12)),
    P("TRAVEL-04", "海边跳跃", "front", (540, 640), -90, armL=(242, 256), armR=(298, 284),
      legL=(58, 124), legR=(68, 112), lifted=True, show_ground=False),
    P("TRAVEL-05", "沙滩望海", "34", (520, 960), -96, armL=(138, 158), armR=(30, 60),
      legL=(26, 94), legR=(34, 98), face=20),
    P("TRAVEL-06", "公路延伸线", "back", (540, 700), -90, armL=(92, 90), legL=(88, 88), legR=(92, 90)),
    P("TRAVEL-07", "道具挡脸", "34", (540, 700), -90, armL=(104, -32), armR=(88, 94), face=10),
    P("TRAVEL-08", "阳台清晨", "34", (540, 700), -95, armL=(246, 262), armR=(250, 255), face=0),
    P("TRAVEL-09", "车窗观景", "side", (500, 700), -88, -80, armL=(84, -70), armR=(92, 96),
      legL=(90, 88), legR=(92, 92), face=0, foot_dir=(1, 1)),
    P("TRAVEL-10", "假装拍摄", "34", (540, 700), -90, armL=(104, -64), armR=(76, 244), face=0),
    # --------------------------------------------------------------- HOME
    P("HOME-01", "窗边侧脸", "side", (500, 700), -90, -85, armL=(60, 20), armR=(95, 92),
      legL=(90, 88), legR=(92, 92), face=0, foot_dir=(1, 1)),
    P("HOME-02", "床上趴姿", "34", (540, 860), -70, -85, armL=(60, 20), armR=(70, 30),
      legL=(88, 235), legR=(94, 240), face=20, ground=1080, show_ground=False),
    P("HOME-03", "俯拍躺姿", "front", (540, 690), -90, armL=(150, 170), armR=(30, 10),
      legL=(84, 86), legR=(96, 94)),
    P("HOME-04", "厨房回头", "34", (540, 700), -90, armL=(30, 20), armR=(100, 96), face=210),
    P("HOME-05", "对镜自拍", "34", (545, 700), -90, armL=(232, 300), armR=(128, 160),
      legL=(92, 86), legR=(88, 92), face=0),
    P("HOME-06", "窗帘氛围", "34", (540, 700), -90, armL=(250, 268), armR=(96, 92), face=0),
    P("HOME-07", "地毯躺拍", "front", (540, 700), -90, armL=(250, 270), armR=(290, 270),
      legL=(88, 86), legR=(94, 90)),
    P("HOME-08", "沙发阅读", "34", (540, 900), -88, armL=(104, -46), legL=(24, 92), legR=(32, 96), face=10),
    P("HOME-09", "阳台植感", "34", (540, 700), -84, armL=(56, -8), armR=(100, 96),
      legL=(98, 88), legR=(86, 90), face=0),
    P("HOME-10", "夜读暖光", "34", (540, 895), -86, -78, armL=(100, -50), legL=(26, 94), legR=(32, 98), face=15),
    # --------------------------------------------------------------- CAFE
    P("CAFE-01", "捧杯看镜头", "34", (540, 895), -88, armL=(100, -64), legL=(24, 92), legR=(32, 96), face=5),
    P("CAFE-02", "举杯遮嘴", "side", (520, 890), -88, armL=(86, -72), armR=(96, 90),
      legL=(22, 94), legR=(30, 98), face=0, foot_dir=(1, 1)),
    P("CAFE-03", "低头看单", "34", (540, 890), -86, -72, armL=(92, -30), legL=(24, 92), legR=(30, 96), face=0),
    P("CAFE-04", "桌面 POV", "34", (540, 880), -84, armL=(26, 10), armR=(146, 170),
      legL=(24, 92), legR=(30, 96), face=0),
    P("CAFE-05", "搅拌特写", "34", (540, 890), -86, -78, armL=(94, -24), legL=(24, 92), legR=(30, 96), face=0),
    P("CAFE-06", "靠窗剪影", "side", (520, 890), -92, -88, armL=(96, 90), armR=(86, 86),
      legL=(20, 94), legR=(28, 98), face=180, foot_dir=(-1, -1)),
    P("CAFE-07", "切蛋糕抓拍", "34", (540, 895), -82, armL=(74, -16), legL=(24, 92), legR=(30, 96), face=15),
    P("CAFE-08", "举杯对碰", "34", (540, 890), -90, armL=(26, -6), armR=(86, 90),
      legL=(24, 92), legR=(30, 96), face=0),
    P("CAFE-09", "阅读氛围", "34", (540, 890), -86, -80, armL=(102, -44), legL=(24, 92), legR=(30, 96), face=10),
    P("CAFE-10", "递物互动", "34", (540, 890), -84, armL=(14, 6), armR=(96, 92),
      legL=(24, 92), legR=(30, 96), face=0),
    # --------------------------------------------------------------- BACK
    P("BACK-01", "张开双臂", "back", (540, 700), -90, armL=(162, 170), armR=(18, 10)),
    P("BACK-02", "回眸 45°", "34", (540, 700), -90, armL=(100, 94), armR=(236, 300),
      legL=(96, 88), legR=(84, 90), face=210),
    P("BACK-03", "举手比心", "back", (540, 700), -90, armL=(244, 262), armR=(296, 278)),
    P("BACK-04", "撑伞背影", "back", (540, 700), -90, armL=(240, 266), armR=(96, 92)),
    P("BACK-05", "高处坐望", "back", (540, 810), -94, armL=(110, 120), armR=(70, 60),
      legL=(88, 94), legR=(92, 90)),
    P("BACK-06", "林荫道居中", "back", (540, 700), -90, armL=(104, 60), armR=(76, 120),
      legL=(102, 88), legR=(78, 90)),
    P("BACK-07", "手提帽子", "back", (540, 700), -90, armL=(96, 78), armR=(108, 66),
      legL=(96, 88), legR=(84, 90)),
    P("BACK-08", "落日剪影", "back", (540, 700), -90, armL=(156, 166), armR=(24, 14),
      legL=(100, 90), legR=(80, 86)),
    P("BACK-09", "低头看花", "34", (535, 715), -76, -60, armL=(110, 150), armR=(100, 96), face=200),
    P("BACK-10", "踢腿跳跃", "back", (540, 690), -90, armL=(250, 262), armR=(290, 275),
      legL=(92, 86), legR=(96, 212), lifted=True, show_ground=False),
    # --------------------------------------------------------------- PROP
    P("PROP-01", "花束挡脸", "34", (540, 700), -90, armL=(96, -46), armR=(90, 94), face=10),
    P("PROP-02", "牵引气球", "34", (540, 700), -90, -84, armL=(250, 266), armR=(96, 92), face=0),
    P("PROP-03", "假装自拍", "34", (545, 700), -90, armL=(234, 300), armR=(130, 160),
      legL=(92, 86), legR=(88, 92), face=0),
    P("PROP-04", "书本挡脸", "34", (540, 700), -90, armL=(108, -40), armR=(72, 220), face=0),
    P("PROP-05", "超市生活流", "34", (540, 700), -86, armL=(18, 6), armR=(110, 74),
      legL=(96, 88), legR=(84, 90), face=200),
    P("PROP-06", "宠物互动", "34", (540, 975), -70, -80, armL=(24, 10), armR=(86, 110),
      legL=(20, 130), legR=(26, 124), face=30),
    P("PROP-07", "单车倚靠", "34", (530, 705), -92, armL=(10, -4), armR=(96, 92),
      legL=(96, 86), legR=(100, 110), face=15),
    P("PROP-08", "泡泡机", "34", (540, 700), -88, -84, armL=(60, -10), armR=(30, 0), face=10),
    P("PROP-09", "耳机氛围", "34", (540, 700), -90, -86, armL=(112, -30), armR=(68, 210), face=0),
    P("PROP-10", "街头美食", "34", (540, 700), -90, armL=(100, -40), armR=(92, 94), face=10),
    # -------------------------------------------------------------- SCENE
    P("SCENE-01", "夜色霓虹回眸", "34", (540, 700), -90, armL=(98, 70), armR=(120, 258),
      legL=(98, 88), legR=(84, 90), face=205),
    P("SCENE-02", "美术馆侧读", "side", (500, 700), -90, armL=(30, -20), armR=(96, 92),
      legL=(90, 88), legR=(92, 92), face=20),
    P("SCENE-03", "书架捧书", "34", (540, 700), -90, -84, armL=(104, -44), armR=(76, 224), face=10),
    P("SCENE-04", "花田拨发", "34", (540, 700), -90, -88, armL=(236, 296), armR=(96, 92), face=0),
    P("SCENE-05", "海堤望海", "34", (540, 1045), -78, armL=(100, 160), armR=(80, 20),
      legL=(262, 72), legR=(279, 85), face=20),
    P("SCENE-06", "伞下听雨", "34", (540, 700), -86, -70, armL=(238, 264), armR=(96, 92), face=0),
    P("SCENE-07", "站台候车", "34", (540, 700), -92, armL=(196, 172), armR=(96, 92), face=200),
    P("SCENE-08", "野餐侧躺", "34", (540, 880), -110, -100, armL=(60, 10), armR=(150, 170),
      legL=(24, 60), legR=(30, 52), face=0, ground=1250),
    P("SCENE-09", "雪地呵手", "34", (540, 700), -90, -86, armL=(100, -62), armR=(80, 242), face=0),
    P("SCENE-10", "机场回眸", "34", (540, 700), -90, armL=(100, 74), armR=(78, 96),
      legL=(100, 88), legR=(80, 90), face=210),
]}


# ---------------------------------------------- 逐条校正（坐姿透视压缩等）
SEAT = dict(view="34", hip=(470, 880), legL=(12, 92), legR=(22, 98), chair=True)  # 3/4 侧坐：大腿前伸、小腿垂直（无椅也读得出「坐」）
SEAT_SIDE = dict(fs=(0.80, 0.95))
FIX = {
    "SIT-01": SEAT, "SIT-03": dict(legL=(58, 80), legR=(120, 92), fs=(0.78, 0.90)),
    "SIT-06": dict(hip=(470, 900), spine=-114, head=-102, legL=(2, -12), legR=(38, 74), fs=(0.80, 0.80)),
    "SIT-08": dict(view="side", hip=(560, 1010), spine=-92, head=-90, face=0, foot_dir=(-1, -1), legL=(95, 180), legR=(99, 184), fs=(1.0, 0.90)),
    "SIT-09": dict(legL=(112, 92), legR=(68, 88), fs=(0.50, 0.95)),
    "SIT-10": dict(fs=(0.80, 0.95)),
    "SIT-02": SEAT_SIDE,
    "CAFE-01": SEAT, "CAFE-02": dict(fs=(0.75, 0.95)), "CAFE-03": SEAT, "CAFE-04": SEAT,
    "CAFE-05": SEAT, "CAFE-06": dict(fs=(0.75, 0.95)), "CAFE-07": SEAT, "CAFE-08": SEAT,
    "CAFE-09": SEAT, "CAFE-10": SEAT,
    "HOME-08": SEAT, "HOME-10": SEAT, "TRAVEL-05": SEAT, "SCENE-08": dict(fs=(0.85, 0.55)),
    "STREET-04": dict(spine=-102, armL=(34, 10), armR=(96, 92), legL=(96, 88), legR=(80, 200), fs=(1.0, 0.72)),
    "HOME-02": dict(hip=(560, 900), spine=176, head=182, armL=(300, 40), armR=(310, 45),
                    legL=(8, -62), legR=(14, -70), fs=(0.92, 0.85), ground=1000),
    "PROP-08": dict(afs=(0.85, 0.80)),
}
CHAIR_IDS = ["SIT-01", "SIT-02", "SIT-09", "SIT-10", "CAFE-01", "CAFE-02", "CAFE-03",
             "CAFE-05", "CAFE-06", "CAFE-07", "CAFE-08", "CAFE-09", "CAFE-10",
             "HOME-08", "HOME-10"]
for _k, _v in FIX.items():
    SPECS[_k].update(_v)
for _k in CHAIR_IDS:
    SPECS[_k]["chair"] = True


def finalize(s):
    """算关节 -> 自适应缩放/落地，保证全部关节落在画幅内。"""
    best = None
    for sc in (1.0, 0.95, 0.90, 0.85, 0.80, 0.74):
        J = build(s, sc)
        top = J["headCenter"][1] - R_HEAD * 1.06 * sc
        bot = max(J["ankleL"][1], J["ankleR"][1]) + 38.0 * sc
        for k in ("wristL", "wristR"):
            top = min(top, J[k][1] - 18.0 * sc)
        hang = max(J["wristL"][1], J["wristR"][1]) + 20
        bot = max(bot, hang if hang < bot + 400 else bot)
        span = bot - top
        best = (J, top, bot, sc)
        if span <= 1268:
            break
    J, top, bot, sc = best
    # 落地：脚底贴到安全线下沿；矮姿势垂直居中
    dy = 1320 - bot
    if bot - top < 1150:
        dy = (110 + 1330) / 2 - (top + bot) / 2
    if top + dy < 34:
        dy += 34 - (top + dy)
    J = {k: (v[0], v[1] + dy) for k, v in J.items()}
    ground = bot + dy
    return J, ground, sc


def joints_of(J, ground):
    hx, hy = J["headCenter"]
    ry = R_HEAD * 1.03
    g = lambda p: [round(p[0] / W0, 5), round(p[1] / H0, 5)]
    return {
        "headTop": g((hx, hy - ry)), "headCenter": g((hx, hy)), "chin": g((hx, hy + ry * 0.94)),
        "shoulderL": g(J["shL"]), "shoulderR": g(J["shR"]),
        "elbowL": g(J["elbowL"]), "elbowR": g(J["elbowR"]),
        "wristL": g(J["wristL"]), "wristR": g(J["wristR"]),
        "hipL": g(J["hipL"]), "hipR": g(J["hipR"]),
        "kneeL": g(J["kneeL"]), "kneeR": g(J["kneeR"]),
        "ankleL": g(J["ankleL"]), "ankleR": g(J["ankleR"]),
        "bodyAxisX": round(J["chest"][0] / W0, 5),
        "footBottomY": round(ground / H0, 5),
    }


def st_joints(pid):
    """ST-01..10：直接取已交付 skeleton SVG 的同一套关节（gen_skeleton.POSES）。"""
    p = ST_POSES[pid]
    g = lambda x, y: [round(x / W0, 5), round(y / H0, 5)]
    hx, hy, hr = p["head"]
    return {
        "headTop": g(hx, hy - hr * 1.03), "headCenter": g(hx, hy), "chin": g(hx, hy + hr * 0.94),
        "shoulderL": g(p["sh"][0], p["sh"][1]), "shoulderR": g(p["sh"][2], p["sh"][3]),
        "elbowL": g(p["elbow"][0], p["elbow"][1]), "elbowR": g(p["elbow"][2], p["elbow"][3]),
        "wristL": g(p["wrist"][0], p["wrist"][1]), "wristR": g(p["wrist"][2], p["wrist"][3]),
        "hipL": g(p["hip"][0], p["hip"][1]), "hipR": g(p["hip"][2], p["hip"][3]),
        "kneeL": g(p["knee"][0], p["knee"][1]), "kneeR": g(p["knee"][2], p["knee"][3]),
        "ankleL": g(p["ankle"][0], p["ankle"][1]), "ankleR": g(p["ankle"][2], p["ankle"][3]),
        "bodyAxisX": round(p["chest"][0] / W0, 5),
        "footBottomY": round(p["ground"] / H0, 5),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--contact", action="store_true")
    ap.add_argument("--ctl-only", action="store_true")
    args = ap.parse_args()

    sk = HERE / "skeleton"
    ctl = HERE / "_ctl"
    sk.mkdir(exist_ok=True)
    ctl.mkdir(exist_ok=True)
    ids = args.ids or list(SPECS)
    joints = {}
    for pid in ids:
        s = dict(SPECS[pid])
        J, ground, sc = finalize(s)
        s2 = dict(s)
        sh = shapes(J, s2, ground, sc)
        joints[pid] = joints_of(J, ground)
        if not args.ctl_only:
            png = render(sh, W0, H0, SK_BG, SK_INK, SK_BODY, SK_SW, ground=ground,
                         show_ground=s.get("show_ground", True))
            png.save(sk / f"{pid}.png", "PNG", optimize=True)
            (sk / f"{pid}.svg").write_text(svg(sh, s, ground), encoding="utf-8")
        big = render(sh, 1728, 2304, CTL_BG, CTL_INK, CTL_BODY, CTL_SW, ground=ground)
        big.save(ctl / f"{pid}.png", "PNG", optimize=True)

    # joints.json：ST 10 + 本批，一次写全
    allj = {f"ST-{i:02d}": st_joints(f"ST-{i:02d}") for i in range(1, 11)}
    if len(ids) == len(SPECS):
        allj.update(joints)
    else:
        prev = HERE / "joints.json"
        if prev.exists():
            allj.update(json.loads(prev.read_text(encoding="utf-8")).get("poses", {}))
        allj.update(joints)
    doc = {
        "meta": {
            "version": 1,
            "canvas": {"w": 3, "h": 4},
            "note": "坐标已归一化到 0-1（3:4）。L/R 按「画面左 / 画面右」标注，不按人物自身左右。"
                    "canvas.w/h 为画幅比例（3:4），像素坐标 = [x*w, y*h]。",
            "unit": "normalized 0-1",
            "lrConvention": "viewer-left / viewer-right",
            "count": len(allj),
        },
        "poses": dict(sorted(allj.items())),
    }
    (HERE / "joints.json").write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(ids)} 张骨架 -> {sk}；joints.json {len(allj)} 条")
    if args.contact:
        print(contact(ids, HERE / "_contact-new.png"))


if __name__ == "__main__":
    main()
