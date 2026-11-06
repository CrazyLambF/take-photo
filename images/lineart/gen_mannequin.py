#!/usr/bin/env python3
"""有体积人偶控制图（volume mannequin）—— 线稿路线 A 的控制图升级实验

背景：上一轮「细线骨架」i2i 控制图在 ST-04/05/07/09 四条全败，失败点全在手臂
（贴躯干 / 跨躯干 / 侧视上举）。假设：细线携带的**体量信息**太少，模型读不出
「这是一条手臂」还是「贴着身体的一条轮廓线」，于是按审美先验把手臂抹平。

本脚本把控制图从「几根等粗的线 + 小圆点」升级为**有体积的人偶**：
  · 躯干 = 胸廓 + 收窄腰 + 骨盆三个体块，接缝处刻意收窄成短弧，读作结构线而不是积木
  · 四肢 = 带锥度的柱体（近端粗、远端细），粗细与朝向一起表达「这条手臂指向哪」
  · 关节 = 实心球（肩/肘/腕/髋/膝/踝），手 = 沿前臂方向的椭球
  · 每个部件独立描边（外扩 OW 画 INK，再压一层 BODY）：叠压处靠各自轮廓分开
  · 白底 + 深灰体块，只留形体，不画衣服 / 五官 / 阴影

坐标复用 gen_skeleton.py 的 POSES（同一套关节语义），仅对 ST-04/05/09 做**与封面
照片的一致性校正**（见下方 POSES_VOL 注释）：原数据在手臂上本来就偏离封面。

用法：
  python3 gen_mannequin.py                 # 三张 AI 控制图（1728x2304）
  python3 gen_mannequin.py --preview       # 附带 1080 预览
"""
import argparse
import copy
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_skeleton import POSES  # noqa: E402

W0, H0 = 1080, 1440

WHITE = (0xFF, 0xFF, 0xFF)
INK = (0x2E, 0x29, 0x25)      # 描边：近黑深灰
BODY = (0x6E, 0x68, 0x60)     # 本体：深灰
DARK = (0x57, 0x52, 0x4B)     # 远侧肢体（侧视分层用）
HI = (0x8C, 0x86, 0x7D)       # 高光：稍亮的中灰（只表达圆润，不画阴影排线）

OW = 4.6                       # 1080 空间的描边宽度

R_UARM = (23.0, 17.5)
R_FARM = (17.5, 13.0)
R_THIGH = (32.0, 24.0)
R_SHANK = (24.0, 15.0)
R_NECK = 24.0
R_HAND = (14.0, 10.5)
BALL = dict(shoulder=22.0, elbow=16.5, wrist=11.0, hip=20.0, knee=17.5, ankle=12.0)

# ---------------------------------------------------------------- 姿势数据校正
# 依据 = images/ST-0x.jpg 封面实拍；判定标准是"能否对照封面看出是同一姿势"。
POSES_VOL = copy.deepcopy(POSES)

# ST-04 双手插袋：原数据两腕 518/570 只差 52px（≈胯宽 1/3），等于"双手在裆前合拢"——
# 这本身就是上轮被画成"手在身前握在一起"的直接原因。封面是牢牢插在胯前袋口，
# 故把手位外移到袋口、肘部收一点（原肘 414/668 张得太开，读作"叉腰"）。
POSES_VOL["ST-04"].update(
    elbow=(430, 620, 652, 618),
    wrist=(496, 738, 592, 736),
)
# ST-05 松弛环抱：原数据两条前臂自下向上交叉成"X"（左右腕 516/528 各跨到对侧），
# 视觉上读作"抱胸打了个叉"。封面的真实动作是两条前臂**近乎水平地上下叠放**、
# 手插进对侧臂弯，故把两腕放到同一水平带、拉开约 70px 的上下间距。
POSES_VOL["ST-05"].update(
    elbow=(438, 618, 648, 642),
    wrist=(598, 562, 470, 632),
)
# ST-09 踮脚伸展：原数据是一手搭眉骨远眺 + 一臂上举（封面并非如此）。
# 封面 = 近侧面、身体后仰、**双臂一并上举过头、双手在头顶相扣**、踮脚。
POSES_VOL["ST-09"].update(
    head=(556, 292, 56), neck=(554, 354), chest=(538, 470),
    sh=(536, 394, 578, 400), hip=(548, 700, 570, 706),
    elbow=(476, 302, 622, 290),
    wrist=(520, 178, 568, 162),
    knee=(540, 986, 562, 992), ankle=(536, 1262, 556, 1268),
)

SPEC = {
    "ST-04": dict(view="front", foot_dir=(-1, 1), rib=0.98, pel=0.80, leg=1.00),
    "ST-05": dict(view="front", foot_dir=(-1, 1), rib=0.98, pel=0.80, leg=1.00),
    "ST-09": dict(view="side", foot_dir=(-1, -1), rib=1.00, pel=1.00, leg=0.88),
}


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


class Mannequin:
    """所有部件走同一条合成路径：外扩画 INK -> 本体画 BODY -> 内切画 HI。"""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.K = W / W0
        self.img = Image.new("RGB", (W, H), WHITE)

    def P(self, p):
        return (p[0] * self.K, p[1] * self.K)

    def R(self, r):
        return max(0.5, r * self.K)

    def _part(self, draw_at, hi_at=None, body=BODY):
        """draw_at(d, grow_px) 在 mask 上画形状；hi_at 同理（高光）。"""
        g = self.R(OW)
        m = Image.new("L", (self.W, self.H), 0)
        dm = ImageDraw.Draw(m)
        draw_at(dm, g)                     # 外扩版 -> 描边层
        self.img.paste(INK, (0, 0), m)
        m2 = Image.new("L", (self.W, self.H), 0)
        dm2 = ImageDraw.Draw(m2)
        draw_at(dm2, 0.0)                  # 本体
        self.img.paste(body, (0, 0), m2)
        if hi_at is not None:
            m3 = Image.new("L", (self.W, self.H), 0)
            hi_at(ImageDraw.Draw(m3))
            self.img.paste(HI, (0, 0), ImageChops.multiply(m3, m2))

    # ---- 基本形 ---------------------------------------------------------
    @staticmethod
    def _capsule(d, p0, p1, r0, r1, fill=255):
        dx, dy = unit(p0, p1)
        nx, ny = -dy, dx
        d.polygon([(p0[0] + nx * r0, p0[1] + ny * r0), (p1[0] + nx * r1, p1[1] + ny * r1),
                   (p1[0] - nx * r1, p1[1] - ny * r1), (p0[0] - nx * r0, p0[1] - ny * r0)],
                  fill=fill)
        for c, r in ((p0, r0), (p1, r1)):
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=fill)

    @staticmethod
    def _ell(d, c, rx, ry, fill=255):
        d.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], fill=fill)

    def limb(self, p0, p1, r0, r1, hi=True, body=BODY):
        a, b = self.P(p0), self.P(p1)
        ra, rb = self.R(r0), self.R(r1)
        draw = lambda d, g: self._capsule(d, a, b, ra + g, rb + g)
        hf = None
        if hi:
            dx, dy = unit(a, b)
            nx, ny = -dy, dx
            if nx * -0.42 + ny * -0.91 < 0:      # 高光统一朝左上
                nx, ny = -nx, -ny
            off = 0.38 * (ra + rb) / 2
            ins = 0.45 * (ra + rb) / 2
            q0 = (a[0] + nx * off + dx * ins, a[1] + ny * off + dy * ins)
            q1 = (b[0] + nx * off - dx * ins, b[1] + ny * off - dy * ins)
            hf = lambda d: self._capsule(d, q0, q1, ra * 0.36, rb * 0.36)
        self._part(draw, hf, body=body)

    def ball(self, p, r, hi=True, body=BODY):
        c = self.P(p)
        rr = self.R(r)
        draw = lambda d, g: self._ell(d, c, rr + g, rr + g)
        hf = (lambda d: self._ell(d, (c[0] - rr * 0.30, c[1] - rr * 0.32),
                                  rr * 0.40, rr * 0.40)) if hi else None
        self._part(draw, hf, body=body)

    def hand(self, wrist, elbow, r0, r1):
        dx, dy = unit(self.P(elbow), self.P(wrist))
        a = self.P(wrist)
        b = (a[0] + dx * self.R(22), a[1] + dy * self.R(22))
        ra, rb = self.R(r0), self.R(r1)
        self._part(lambda d, g: self._capsule(d, a, b, ra + g, rb + g), None)

    # ---- 体块：左右两条半宽曲线（可做胸/臀凸起与侧视 S 形） ----------------
    def mass(self, y0, y1, keysL, keysR, cx_fn, hi=True, n=72):
        right, left = [], []
        for i in range(n + 1):
            t = i / n
            y = (y0 + (y1 - y0) * t) * self.K
            cx = cx_fn(t) * self.K
            right.append((cx + self._interp(keysR, t) * self.K, y))
            left.append((cx - self._interp(keysL, t) * self.K, y))
        poly = right + list(reversed(left))

        def draw(d, g):
            d.polygon(poly, fill=255)
            if g > 0:
                d.line(poly + [poly[0]], fill=255, width=int(round(2 * g)),
                       joint="curve")

        hf = None
        if hi:
            cx = cx_fn(0.45) * self.K
            w = max(self._interp(keysL, 0.45), self._interp(keysR, 0.45)) * self.K
            hc = (cx - w * 0.30, (y0 + (y1 - y0) * 0.40) * self.K)
            hf = lambda d: self._ell(d, hc, w * 0.26, (y1 - y0) * 0.30 * self.K)
        self._part(draw, hf)

    @staticmethod
    def _interp(keys, t):
        keys = sorted(keys)
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, w0), (t1, w1) in zip(keys, keys[1:]):
            if t <= t1:
                u = (t - t0) / max(1e-6, t1 - t0)
                return w0 + (w1 - w0) * (u * u * (3 - 2 * u))
        return keys[-1][1]

    def head(self, p, side=False):
        hx, hy, hr = p["head"]
        rx, ry = hr * (0.94 if side else 0.83), hr * 1.03
        c = self.P((hx, hy))
        R = self.R
        draw = lambda d, g: self._ell(d, c, R(rx) + g, R(ry) + g)
        hf = lambda d: self._ell(d, (c[0] - R(rx) * 0.32, c[1] - R(ry) * 0.34),
                                 R(rx) * 0.42, R(ry) * 0.38)
        self._part(draw, hf)
        face = p.get("face")
        if face is not None:                         # 侧脸：鼻尖
            a = math.radians(face)
            nc = (c[0] + math.cos(a) * R(rx * 0.94), c[1] + math.sin(a) * R(ry) * 0.05)
            self._part(lambda d, g: self._ell(d, nc, R(hr * 0.19) + g, R(hr * 0.12) + g), None)

    def foot(self, ankle, direction, ground, tiptoe=False, body=BODY):
        a = self.P(ankle)
        gy = ground * self.K
        toe = (a[0] + direction * self.R(46), gy - self.R(7))
        ra, rb = self.R(16.0), self.R(10.0)
        if tiptoe:
            def draw(d, g):
                self._capsule(d, a, toe, ra + g, rb + g)
                self._ell(d, (a[0] - direction * self.R(9), a[1] + self.R(6)),
                          self.R(9) + g, self.R(9) + g)
        else:
            heel = (a[0] - direction * self.R(12), gy - self.R(8))
            def draw(d, g):
                self._capsule(d, a, toe, ra + g, rb + g)
                self._capsule(d, heel, toe, self.R(9) + g, self.R(8) + g)
        self._part(draw, None, body=body)


def draw_pose(p, W, H, spec):
    m = Mannequin(W, H)
    shl, shr = (p["sh"][0], p["sh"][1]), (p["sh"][2], p["sh"][3])
    hl, hr_ = (p["hip"][0], p["hip"][1]), (p["hip"][2], p["hip"][3])
    el, er = (p["elbow"][0], p["elbow"][1]), (p["elbow"][2], p["elbow"][3])
    wl, wr = (p["wrist"][0], p["wrist"][1]), (p["wrist"][2], p["wrist"][3])
    kl, kr = (p["knee"][0], p["knee"][1]), (p["knee"][2], p["knee"][3])
    al, ar = (p["ankle"][0], p["ankle"][1]), (p["ankle"][2], p["ankle"][3])
    neck = (p["neck"][0], p["neck"][1])
    chest = (p["chest"][0], p["chest"][1])
    side = spec["view"] == "side"
    ground = p.get("ground", 1305)
    cx = (shl[0] + shr[0]) / 2

    shw = (shr[0] - shl[0]) / 2
    rib_w = (54.0 if side else shw * 0.96) * spec["rib"]
    pel_w = (50.0 if side else rib_w * 0.80) * spec["pel"]

    rib_top = shl[1] - 2
    rib_bot = chest[1] + (hl[1] - chest[1]) * 0.48
    pel_top = hl[1] - 36
    pel_bot = hl[1] + 60
    lgl = spec["leg"]

    R_TH = (R_THIGH[0] * lgl, R_THIGH[1] * lgl)
    R_SH = (R_SHANK[0] * lgl, R_SHANK[1] * lgl)

    arms = {"L": (shl, el, wl), "R": (shr, er, wr)}

    def draw_arm(key):
        sh, eb, wr_ = arms[key]
        m.limb(sh, eb, *R_UARM)
        m.ball(sh, BALL["shoulder"])
        m.ball(eb, BALL["elbow"])
        m.limb(eb, wr_, *R_FARM)
        m.ball(wr_, BALL["wrist"])
        m.hand(wr_, eb, *R_HAND)

    def draw_legs():
        near = (hl, kl, al, spec["foot_dir"][0])
        far = (hr_, kr, ar, spec["foot_dir"][1])
        legs = [(far, DARK), (near, BODY)] if side else [(near, BODY), (far, BODY)]
        for (hj, kn, an, fd), tone in legs:
            m.limb(hj, kn, *R_TH, hi=False, body=tone)
            m.limb(kn, an, *R_SH, hi=False, body=tone)
            m.ball(kn, BALL["knee"], hi=False, body=tone)
            m.foot(an, fd, ground, tiptoe=bool(p.get("toe")), body=tone)

    # ST-09 侧视：远侧手臂先沉底，才不会被躯干和头压住
    if side:
        draw_arm("R")

    draw_legs()

    # 腰（两端刻意收窄，接缝被胸廓/骨盆盖住，只露出短弧）
    m.mass(rib_bot - 14, pel_top + 14,
           [(0.0, rib_w * 0.50), (0.5, rib_w * 0.52), (1.0, pel_w * 0.58)],
           [(0.0, rib_w * 0.50), (0.5, rib_w * 0.52), (1.0, pel_w * 0.58)],
           lambda t: cx, hi=False)

    # 骨盆
    if side:
        m.mass(pel_top, pel_bot,
               [(0.0, pel_w * 0.52), (0.18, pel_w * 0.92), (0.48, pel_w * 0.98),
                (0.74, pel_w * 0.94), (1.0, pel_w * 0.60)],
               [(0.0, pel_w * 0.62), (0.20, pel_w * 1.04), (0.52, pel_w * 1.00),
                (0.80, pel_w * 0.78), (1.0, pel_w * 0.60)],
               lambda t: hl[0] + (hr_[0] - hl[0]) * t * 0.4, hi=False)
    else:
        m.mass(pel_top, pel_bot,
               [(0.0, pel_w * 0.52), (0.16, pel_w * 0.94), (0.42, pel_w * 1.0),
                (0.74, pel_w * 1.0), (1.0, pel_w * 0.56)],
               [(0.0, pel_w * 0.52), (0.16, pel_w * 0.94), (0.42, pel_w * 1.0),
                (0.74, pel_w * 1.0), (1.0, pel_w * 0.56)],
               lambda t: cx, hi=False)

    # 胸廓（肩宽在这里体现；侧视把胸提到前侧、背略平）
    if side:
        m.mass(rib_top, rib_bot,
               [(0.0, rib_w * 0.60), (0.22, rib_w * 0.98), (0.34, rib_w * 1.06),
                (0.62, rib_w * 0.96), (0.86, rib_w * 0.70), (1.0, rib_w * 0.40)],
               [(0.0, rib_w * 0.80), (0.20, rib_w * 0.92), (0.55, rib_w * 0.90),
                (0.82, rib_w * 0.74), (1.0, rib_w * 0.40)],
               lambda t: chest[0] + (hl[0] - chest[0]) * t)
    else:
        m.mass(rib_top, rib_bot,
               [(0.0, rib_w * 0.86), (0.06, rib_w * 0.96), (0.20, rib_w * 1.0),
                (0.55, rib_w * 0.98), (0.84, rib_w * 0.74), (1.0, rib_w * 0.40)],
               [(0.0, rib_w * 0.86), (0.06, rib_w * 0.96), (0.20, rib_w * 1.0),
                (0.55, rib_w * 0.98), (0.84, rib_w * 0.74), (1.0, rib_w * 0.40)],
               lambda t: cx)

    # 颈 + 头
    m.limb((p["head"][0], p["head"][1] + p["head"][2] * 0.62), (neck[0], rib_top + 10),
           R_NECK, R_NECK * 0.9, hi=False)
    m.head(p, side=side)

    # 手臂：正视两条都压在躯干之上（靠各自轮廓分开）；侧视只补近侧
    if side:
        draw_arm("L")
    else:
        draw_arm("L")
        draw_arm("R")
    return m.img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", default=["ST-04", "ST-05", "ST-09"])
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    for pid in args.ids:
        p = POSES_VOL[pid]
        big = draw_pose(p, 2304, 3072, SPEC[pid])
        ai = big.resize((1728, 2304), Image.LANCZOS)
        out = HERE / f"_vol-ai-{pid}.png"
        ai.save(out, "PNG", optimize=True)
        line = f"{pid} {p['name']:<8} -> {out.name} {out.stat().st_size / 1024:.1f}KB"
        if args.preview:
            pv = big.resize((1080, 1440), Image.LANCZOS)
            pv.save(HERE / f"_vol-preview-{pid}.png", "PNG", optimize=True)
        print(line)


if __name__ == "__main__":
    main()
