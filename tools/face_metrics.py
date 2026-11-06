#!/usr/bin/env python3
"""线稿「五官是否存在」的量化指标（无外部模型依赖）。

思路：人脸五官是画在脸部椭圆**内部**、且与头部外轮廓**不连通**的短墨迹。
空白脸 -> 头部内部没有独立墨迹分量（只有外轮廓与头发）；有五官 -> 存在
若干不连通的小分量（眉/眼/鼻/唇）。

输出：inside_comps（分量数）、inside_px（内部墨迹像素）、face_density。
"""
import sys
import numpy as np
from PIL import Image

FG = np.array([0x3B, 0x36, 0x30])


def ink_mask(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
    return np.abs(a - FG).sum(-1) < 90


def components(mask):
    """4 连通分量标记（纯 numpy，无 scipy）。返回 (labels, n, sizes)。"""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    cur = 0
    sizes = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if labels[y0, x0]:
            continue
        cur += 1
        stack = [(y0, x0)]
        labels[y0, x0] = cur
        n = 0
        while stack:
            cy, cx = stack.pop()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur
                    stack.append((ny, nx))
        sizes.append(n)
    return labels, cur, sizes


def measure(path, head_frac=0.17, face_lo=0.34, face_hi=0.98):
    m = ink_mask(path)
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H = y1 - y0 + 1
    hb = int(H * head_frac)
    crop = m[y0:y0 + hb, :]
    cy, cx = np.nonzero(crop)
    if len(cy) == 0:
        return None
    hy0, hy1, hx0, hx1 = cy.min(), cy.max(), cx.min(), cx.max()
    hh, hw = hy1 - hy0 + 1, hx1 - hx0 + 1

    lab, n, sizes = components(crop)
    outline = 1 + int(np.argmax(sizes))  # 最大分量为外轮廓/身体
    inside_px, inside_comps, per = 0, 0, []
    for i in range(1, n + 1):
        if i == outline:
            continue
        yy, xx = np.nonzero(lab == i)
        ry = (yy.mean() - hy0) / hh
        if face_lo <= ry <= face_hi and hx0 <= xx.mean() <= hx1 and sizes[i - 1] >= 8:
            inside_px += sizes[i - 1]
            inside_comps += 1
            per.append(sizes[i - 1])
    face_area = hw * hh * (face_hi - face_lo)
    return dict(inside_comps=int(inside_comps), inside_px=int(inside_px),
                face_density=round(float(inside_px / max(face_area, 1)), 5),
                head_w=int(hw), head_h=int(hh), body_h=int(H),
                comp_px=[int(v) for v in sorted(per, reverse=True)[:8]])


if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = measure(p)
        print(p, r)
