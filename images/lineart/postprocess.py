#!/usr/bin/env python3
"""线稿后处理：AI 出图 -> 1080x1440 统一双色 PNG（<=20KB）

后处理是**风格一致性的兜底**：AI 每张的线宽/灰度/底色都会漂，这里用一次确定性的
调色板映射把全部 10 张压成同一套「深炭灰墨线 + 奶油底」，跨图差异只剩构图本身。

 pipeline：
   1. 1728x2304 -> 1080x1440（LANCZOS）
   2. 灰度 -> 自动白平衡（把纸白拉到 255）+ 对比拉伸
   3. 三级量化：ink(<t1) / mid(t1..t2 软化为 ink 决策) / paper(>t2) -> 二值
   4. 去孤点（连通过小的噪点）
   5. 调色板映射到 FG/BG，PNG optimize 落盘

用法：python3 postprocess.py trial/raw-ST-01-A.jpg -o out.png [--check]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

FG = (0x3B, 0x36, 0x30)        # 深炭灰墨线
BG = (0xF6, 0xF0, 0xE5)        # 品牌奶油底
W, H = 1080, 1440
LIMIT = 20 * 1024
# 与 gen_skeleton.py 的关节坐标同一空间；骨架 -> 落图的对齐框
SK_TOP, SK_BOT = 234, 1305     # 骨架头顶 / 脚底（1080x1440 空间）


def binarize(gray: np.ndarray, t1=150, t2=232) -> np.ndarray:
    """返回 ink 布尔图。t1 以下必为墨，t1..t2 之间按软阈值，t2 以上为纸。"""
    g = gray.astype(np.float32)
    ink = g <= t1
    soft = (g > t1) & (g <= t2)
    # 软区用局部对比补线：中间灰且明显暗于局部纸白 -> 判为墨
    if soft.any():
        ink |= soft & (g < (t1 + t2) / 2)
    return ink


def dilate(ink: np.ndarray, n=1) -> np.ndarray:
    """4 连通膨胀 n 次，补回二值化丢掉的线宽。

    实测 n=1 是最优点：细线不再断续，人脸五官仍分得开；n=2 会让眼睛糊成块。
    附带好处：笔画更连贯 -> PNG 压缩率更高（16.8KB -> 14.9KB）。
    """
    r = ink.copy()
    for _ in range(n):
        b = r.copy()
        b[1:, :] |= r[:-1, :]
        b[:-1, :] |= r[1:, :]
        b[:, 1:] |= r[:, :-1]
        b[:, :-1] |= r[:, 1:]
        r = b
    return r


def despeckle(ink: np.ndarray, min_px=6) -> np.ndarray:
    """去掉极小的孤立噪点块（4 连通）。纯 numpy，无 scipy 依赖。"""
    out = ink.copy()
    seen = np.zeros_like(ink)
    h, w = ink.shape
    for y in range(h):
        row = ink[y]
        if not row.any():
            continue
        x = 0
        while x < w:
            if row[x] and not seen[y, x]:
                stack = [(y, x)]
                seen[y, x] = True
                comp = []
                while stack:
                    cy, cx = stack.pop()
                    comp.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and ink[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                if len(comp) < min_px:
                    for cy, cx in comp:
                        out[cy, cx] = False
            x += 1
    return out


def process(src: Path, dst: Path, pad=True, dil=1):
    im = Image.open(src).convert("RGB")
    # 居中裁到 3:4 再缩放（模型可能给非精确 3:4）
    tw, th = W, H
    sw, sh = im.size
    if sw / sh > tw / th:
        nw = int(sh * tw / th)
        im = im.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    else:
        nh = int(sw * th / tw)
        im = im.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
    im = im.resize((tw, th), Image.LANCZOS)

    gray = np.asarray(im.convert("L"), dtype=np.uint8)
    # 白平衡：把 99 分位当纸白归一化
    p99 = np.percentile(gray, 99)
    if p99 < 250 and p99 > 0:
        gray = np.clip(gray.astype(np.float32) * (255.0 / p99), 0, 255).astype(np.uint8)

    ink = binarize(gray)
    ink = despeckle(ink, min_px=5)
    if dil:
        ink = dilate(ink, dil)

    arr = np.zeros((th, tw, 3), dtype=np.uint8)
    arr[:] = BG
    arr[ink] = FG
    out = Image.fromarray(arr, "RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, "PNG", optimize=True)
    return dst.stat().st_size, float(ink.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srcs", nargs="+")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    rows = []
    for s in args.srcs:
        src = Path(s)
        dst = Path(args.out) if (args.out and len(args.srcs) == 1) else src.with_name(
            src.stem.replace("raw-", "").split("-")[0] + "-final.png")
        size, coverage = process(src, dst)
        rows.append(dict(src=src.name, out=dst.name, bytes=size,
                         kb=round(size / 1024, 1), pass_=size <= LIMIT,
                         ink_ratio=round(coverage, 4)))
        print(f"{src.name:28s} -> {dst.name:22s} {size / 1024:6.1f}KB "
              f"{'OK' if size <= LIMIT else 'OVER'} ink={coverage:.3f}")
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == "__main__":
    main()
