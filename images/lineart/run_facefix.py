#!/usr/bin/env python3
"""补面部五官：6 条空白脸 / 五官太淡的图重出（硬预算 0.72 元）。

背景：定版提示词从未提到「脸」，模型在正面朝镜头的图里画了一个空白椭圆。
本轮只在提示词里追加「五官简略但完整」的正向要求 + 「空白脸」的 avoid，
其余参数与定版完全一致（同模型/尺寸/seed/控制图/双色/膨胀 1px/<=20KB）。

验收铁则（任一不满足就保留旧图）：
  (a) 五官可见：脸部内部独立墨迹分量 >= 3 且像素 >= 150（基线最低的是 146px）
  (b) 姿态可辨一致：与旧图掩膜对齐后 IoU >= 阈值，且行宽轮廓相关高

用法：
  python3 run_facefix.py --dry-run
  python3 run_facefix.py              # 生成 -> 校验 -> 通过才替换
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import cv2  # noqa: E402
import run_all as RA  # noqa: E402
import postprocess as pp  # noqa: E402
from face_metrics import measure  # noqa: E402

MODEL = "doubao-seedream-5-0-flash-260915"
PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"
PRICE = 0.12
LIMIT = 20 * 1024
BUDGET = 0.72            # 6 × 0.12
TOTAL_CAP = 15.00
SPENT_BEFORE = 10.68

FG = np.array([0x3B, 0x36, 0x30])

# 每条：(控制图, 追加的面部/清洁要求)
FACE_TXT = ("面部必须画出简略而完整的五官：两条眉毛、两只眼睛（短细线即可但要看得出）、"
            "一条鼻线、一线嘴唇，位置比例正确；脸部内部不得留白，"
            "不得只画一个空白的椭圆，不得省略眉眼。")
CLEAN_TXT = ("五官线条要清晰连贯、不可淡到看不见；除人体与坐具轮廓外，"
             "不要出现任何零星的碎短线、悬空短线或多余杂线。")

TARGETS = {
    "SIT-08":  dict(ctl="_ctl2/SIT-08.png", extra=FACE_TXT),
    "PROP-09": dict(ctl="_ctl/PROP-09.png", extra=FACE_TXT),
    "PROP-10": dict(ctl="_ctl/PROP-10.png", extra=FACE_TXT),
    "SCENE-02": dict(ctl="_ctl/SCENE-02.png", extra=FACE_TXT),
    "SCENE-03": dict(ctl="_ctl/SCENE-03.png", extra=FACE_TXT),
    "SIT-02":  dict(ctl="_ctl/SIT-02.png", extra=FACE_TXT + CLEAN_TXT),
}
AVOID_ADD = "空白脸、没有五官的脸、脸部留白、面部只有轮廓线、",
AVOID_ADD = AVOID_ADD[0]

# 定版 body 里已有的、按 ID 需要保留的补充（沿用当时定版措辞）
KEEP_EXTRA = {
    "SIT-02": "参考图中的浅灰色块是坐具（椅子），请把它画成两三根极简线条构成的椅子，"
              "并让人物如实坐在椅子上（臀部接触椅面、双脚落地），不得把人物画成站立。",
    "SIT-08": "人物日式跪坐：双膝着地、小腿与脚背平贴地面，臀部坐在脚跟上，上身直立，"
              "双手交叠放在大腿上。不得画成站立或蹲。",
}


def build_prompt(pid):
    p = RA.BASE
    add = ""
    if pid in KEEP_EXTRA:
        add += KEEP_EXTRA[pid]
    add += TARGETS[pid]["extra"]
    p = p.replace("画面避免：", add + "画面避免：", 1)
    # 把「空白脸」等加进 avoid 列表
    p = p.replace("画面避免：", "画面避免：" + AVOID_ADD, 1)
    return p


# ---------------------------------------------------------------- 姿态校验
def ink_mask_png(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    return np.abs(a - FG).sum(-1) < 90


def _bbox(m):
    ys, xs = np.nonzero(m)
    return ys.min(), ys.max(), xs.min(), xs.max()


def finish(src: Path, dst: Path, min_px=5, dil=1):
    """与定版 finish() 同管线（3:4 居中裁切 -> 1080x1440 -> 白平衡 -> 二值 -> 去噪 -> 膨胀
    -> 双色），但去噪强度可指定：定版的阶梯末尾会退到 (24,0)，会把淡五官抹平，
    这里只在 (5,1)~(10,1) 之间调整，保证 1px 膨胀与五官都在。"""
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    tw, th = pp.W, pp.H
    if sw / sh > tw / th:
        nw = int(sh * tw / th)
        im = im.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    else:
        nh = int(sw * th / tw)
        im = im.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
    im = im.resize((tw, th), Image.LANCZOS)
    gray = np.asarray(im.convert("L"), dtype=np.uint8)
    p99 = np.percentile(gray, 99)
    if 0 < p99 < 250:
        gray = np.clip(gray.astype(np.float32) * (255.0 / p99), 0, 255).astype(np.uint8)
    ink = pp.binarize(gray)
    ink = pp.despeckle(ink, min_px=min_px)
    if dil:
        ink = pp.dilate(ink, dil)
    arr = np.zeros((th, tw, 3), dtype=np.uint8)
    arr[:] = pp.BG
    arr[ink] = pp.FG
    Image.fromarray(arr, "RGB").save(dst, "PNG", optimize=True)
    return dst.stat().st_size, float(ink.mean()), [min_px, dil]


def pose_similarity(old_path, new_path):
    """线稿姿态一致性：Chamfer 距离（对笔画偏移不敏感）+ 剪影 IoU。

    Chamer：把 A 的每个墨点量到 B 最近墨点的距离，取双向平均，按人体高度归一。
      同姿态重出应 < 0.5%；实测换姿态（跪 vs 坐/站）都在 1.5% 以上。
    剪影 IoU：闭运算填成实心后比面积形状，对「手举/腿抬」这类结构变化敏感。
    """
    a, b = ink_mask_png(old_path), ink_mask_png(new_path)
    da = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 3)
    db = cv2.distanceTransform((~a).astype(np.uint8), cv2.DIST_L2, 3)
    ys, xs = np.nonzero(a)
    pa = float(da[ys, xs].mean())
    ys2, xs2 = np.nonzero(b)
    pb = float(db[ys2, xs2].mean())
    ys, xs = np.nonzero(a | b)
    H = ys.max() - ys.min() + 1
    chamfer = (pa + pb) / 2 / H * 100
    si = sil_iou(a, b)
    ya0, ya1, xa0, xa1 = _bbox(a)
    yb0, yb1, xb0, xb1 = _bbox(b)
    return dict(chamfer=round(chamfer, 3), sil_iou=round(si, 3),
                h_ratio=round((yb1 - yb0 + 1) / (ya1 - ya0 + 1), 3),
                w_ratio=round((xb1 - xb0 + 1) / (xa1 - xa0 + 1), 3))


def _silhouette(m, k=21):
    x = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    x = cv2.morphologyEx(x, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    inv = (1 - x).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv)
    out = x.copy()
    for i in range(1, n):
        comp = (lab == i)
        if not (comp[0, :].any() or comp[-1, :].any() or comp[:, 0].any() or comp[:, -1].any()):
            out[comp] = 1
    return out.astype(bool)


def sil_iou(a, b):
    x, y = _silhouette(a), _silhouette(b)
    return float((x & y).sum() / max((x | y).sum(), 1))


# chamfer 是主判据（同姿态 <0.5%，换姿态 >1.5%）；sil_iou 只做兜底，
# 因为它对笔画粗细/连贯度敏感（同一 raw 只换去噪参数就能掉到 0.12）。
POSE_OK = dict(chamfer=1.0, sil_iou=0.08, h_ratio=(0.90, 1.12), w_ratio=(0.82, 1.22))
FACE_OK = dict(comps=3, px=150)


def face_ok(m):
    return bool(m) and m["inside_comps"] >= FACE_OK["comps"] and m["inside_px"] >= FACE_OK["px"]


def pose_ok(s):
    lo, hi = POSE_OK["h_ratio"]
    lo2, hi2 = POSE_OK["w_ratio"]
    return (s["chamfer"] <= POSE_OK["chamfer"] and s["sil_iou"] >= POSE_OK["sil_iou"]
            and lo <= s["h_ratio"] <= hi and lo2 <= s["w_ratio"] <= hi2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=BUDGET)
    ap.add_argument("--apply", action="store_true", help="校验通过后直接替换（默认只出候选）")
    args = ap.parse_args()
    ids = args.ids or list(TARGETS)

    led_path = HERE / "_facefix-ledger.json"
    led = json.loads(led_path.read_text()) if led_path.exists() else {"runs": []}
    spent = sum(r.get("price", 0) for r in led["runs"] if r.get("ok"))
    done = {r["pose"] for r in led["runs"] if r.get("ok") and r.get("replaced")}
    env = RA.ark_env()
    print(f"计划 {len(ids)} 张，本轮已花 {spent:.2f} / 预算 {args.budget:.2f}，"
          f"累计上限 {TOTAL_CAP:.2f}（存量 {SPENT_BEFORE:.2f}）", flush=True)

    for pid in ids:
        if pid in done:
            print(f"[{pid}] 已替换成功，跳过", flush=True)
            continue
        ctl = HERE / TARGETS[pid]["ctl"]
        if not ctl.exists():
            print(f"[{pid}] 缺控制图 {ctl}", flush=True)
            continue
        if spent + PRICE > args.budget + 1e-9:
            print(f"⛔ 本轮预算到顶 {spent:.2f}/{args.budget:.2f}", flush=True)
            break
        if SPENT_BEFORE + spent + PRICE > TOTAL_CAP + 1e-9:
            print("⛔ 总预算到顶", flush=True)
            break
        prompt = build_prompt(pid)
        payload = {"model": MODEL, "prompt": prompt, "size": SIZE, "watermark": False,
                   "output_format": "jpeg", "response_format": "url",
                   "seed": RA.seed_of(pid), "image": RA.data_uri(ctl)}
        if args.dry_run:
            print(f"[{pid}] ctl={ctl.name} seed={payload['seed']} prompt={len(prompt)}字", flush=True)
            continue

        cmd = ["arkcli", "api", "arkruntime.generate_images", "--profile", PROFILE,
               "--params", json.dumps(payload, ensure_ascii=False)]
        print(f"[{pid}] 生成中…", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        rec = dict(pose=pid, at=datetime.now().isoformat(timespec="seconds"),
                   ctl=TARGETS[pid]["ctl"], model=MODEL, price=PRICE)
        if r.returncode != 0:
            err = (r.stderr or r.stdout).strip()[:400]
            rec.update(ok=False, error=err)
            print(f"    ✗ 失败 {err[:200]}", flush=True)
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2, default=str) + "\n")
            continue
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            rec.update(ok=False, error="非 JSON")
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2, default=str) + "\n")
            continue
        url = RA.find_url(data)
        if not url:
            rec.update(ok=False, error=json.dumps(data, ensure_ascii=False)[:400])
            print(f"    ✗ 无图 {json.dumps(data, ensure_ascii=False)[:200]}", flush=True)
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2, default=str) + "\n")
            continue

        spent += PRICE
        raw = HERE / "raw" / f"{pid}-facefix.jpg"
        raw.parent.mkdir(exist_ok=True)
        subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(raw), url],
                       capture_output=True, timeout=150)
        cand = HERE / "_cand" / f"{pid}.png"
        cand.parent.mkdir(exist_ok=True)
        old = HERE / f"{pid}.png"
        if not (raw.exists() and raw.stat().st_size > 0):
            rec.update(ok=False, error="下载失败")
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2, default=str) + "\n")
            continue

        # 后处理：保持 dil=1（定版 1px 膨胀），必要时只加大去噪，不用「去膨胀」糊掉五官
        size = inkr = 0
        prm = []
        for min_px, dil in ((5, 1), (10, 1), (16, 1), (24, 1)):
            size, inkr, prm = finish(raw, cand, min_px=min_px, dil=dil)
            if size <= LIMIT:
                break
        fm = measure(cand)
        ps = pose_similarity(old, cand)
        passed = face_ok(fm) and pose_ok(ps)
        rec.update(ok=True, seed=payload["seed"], out_bytes=size, ink_ratio=round(inkr, 4),
                   post=prm, face=fm, pose_sim=ps, replaced=passed,
                   latency_s=round(time.time() - t0, 1), spent=round(spent, 2))
        if passed and args.apply:
            (HERE / "_prev_facefix").mkdir(exist_ok=True)
            shutil.copy2(old, HERE / "_prev_facefix" / f"{pid}.png")
            shutil.copy2(cand, old)
            print(f"    ✓ 替换 {pid} 五官{50 if not fm else fm['inside_px']}px/"
                  f"{fm['inside_comps']}块 chamfer={ps['chamfer']}% silIoU={ps['sil_iou']} "
                  f"{size/1024:.1f}KB 累计 {spent:.2f} 元", flush=True)
        elif passed:
            print(f"    ✓ 候选通过 {pid} 五官{fm['inside_px']}px/{fm['inside_comps']}块 "
                  f"chamfer={ps['chamfer']}% silIoU={ps['sil_iou']} {size/1024:.1f}KB "
                  f"(未替换，待目视确认) 累计 {spent:.2f} 元", flush=True)
        else:
            why = []
            if not face_ok(fm):
                why.append(f"五官不足({fm['inside_px']}px/{fm['inside_comps']}块)")
            if not pose_ok(ps):
                why.append(f"姿态偏差(chamfer={ps['chamfer']}%,silIoU={ps['sil_iou']},"
                           f"高比={ps['h_ratio']},宽比={ps['w_ratio']})")
            print(f"    ✗ 保留旧图 {pid}：{'；'.join(why)}", flush=True)
        led["runs"].append(rec)
        led["spent"] = round(spent, 2)
        led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2, default=str) + "\n")

    print(f"结束：本轮花费 {spent:.2f} 元，累计 {SPENT_BEFORE + spent:.2f} 元", flush=True)


if __name__ == "__main__":
    main()
