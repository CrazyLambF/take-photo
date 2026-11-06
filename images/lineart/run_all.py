#!/usr/bin/env python3
"""全量 AI 线稿（路线 A + 有体积人偶控制图），硬预算 15.00 元

流程：_ctl/{ID}.png（体块控制图） + 定版提示词 + seed=md5(ID) -> seedream
      -> 立即 curl -> 后处理（双色 #3B3630/#F6F0E5、膨胀 1px、<=20KB）-> {ID}.png

用法：
  python3 run_all.py --dry-run
  python3 run_all.py --ids SIT-01 CAFE-01
  python3 run_all.py --resume            # 跳过台账里已成功的
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import postprocess as pp  # noqa: E402
from gen_skeleton_all import SPECS  # noqa: E402

MODEL = "doubao-seedream-5-0-flash-260915"
PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"
PRICE = 0.12
BUDGET = 15.00
LIMIT = 20 * 1024

# 定版提示词（上一轮 volume-mannequin 版；控制图为人体人偶）
BASE = (
    "将参考图中的人体人偶（艺术家木人台模型）重绘为杂志风时装速写线稿："
    "画面只保留单色深炭灰墨线，参考图里所有的深灰实体块一律改为**空心轮廓线**，"
    "不要填色、不要保留任何灰色色块，不画阴影、不画排线、不画面料纹理，纯白背景。"
    "参考图是人体模型，请把其中的柱体与球体理解为对应的人体部位（头、颈、胸廓、骨盆、"
    "大臂、前臂、大腿、小腿、手、脚），并补出完整女性人体轮廓与主要结构线。"
    "人物为年轻女性，穿贴身纯色连体练功服、线条简洁的平底鞋，发型简洁。"
    "四肢的位置、弯曲、粗细方向，以及手臂与躯干的相对关系必须与参考图完全一致。"
    "全身姿态与参考图完全一致，竖构图，头顶与脚下留白，人物居中，全身完整入画不裁切。"
    "画面避免：灰阶过渡、灰色填色块、铅笔颗粒、文字、数字、标注、箭头、边框、背景环境、"
    "道具、外套、图案花纹。"
)

# 遮挡类（手插袋/抱膝/手藏背后/手扶腰侧/道具挡脸）：直接留矢量骨架，不花钱
SKIP = {
    "SIT-04": "盘腿+手撑地(腿脚重叠)",
    "SIT-05": "抱膝(手臂环抱遮挡)",
    "SIT-06": "瘫坐扶手(腿搭扶手/手压身下)",
    "SIT-07": "手撑背后(手藏身后)",
    "SIT-08": "跪坐(双手叠放腿间)",
    "SIT-09": "反坐椅背(下巴搁手背,面部遮挡)",
    "SIT-03": "台阶坐(需台阶支撑物)",
    "CAFE-04": "桌面POV(只有手入镜)",
    "HOME-02": "趴姿(肘撑床/脸压枕)",
    "HOME-05": "对镜自拍(手扶腰/手机挡脸)",
    "PROP-03": "假装自拍(手机挡脸)",
    "SCENE-05": "抱膝坐(手臂环抱)",
    "TRAVEL-05": "沙滩坐(需沙地/手撑地)",
    "BACK-05": "堤岸坐望(需边沿支撑物)",
    "SCENE-08": "野餐侧躺(手撑头/布面)",
}

ORDER = [p for p in SPECS]


def seed_of(pid):
    return int(hashlib.md5(pid.encode()).hexdigest()[:8], 16) % 2147483647


def ark_env():
    env = dict(os.environ)
    env.update(
        HOME="/var/folders/w0/2mw6jbm53fxbkgds_6d3504c0000gp/T/arkcli-poseguide-home",
        ARKCLI_NO_UPDATE_NOTIFIER="1",
        ARKCLI_CALLER_TYPE="ai_agent",
        ARKCLI_CALLER_NAME="dsh-takephoto-main",
        ARKCLI_SKILL_NAME="arkcli-gen",
    )
    return env


def data_uri(p):
    return "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()


def find_url(o):
    if isinstance(o, dict):
        d = o.get("data")
        if isinstance(d, list) and d and isinstance(d[0], dict) and d[0].get("url"):
            return d[0]["url"]
        for v in o.values():
            u = find_url(v)
            if u:
                return u
    elif isinstance(o, list):
        for v in o:
            u = find_url(v)
            if u:
                return u
    return None


def finish(src: Path, dst: Path):
    """1728x2304 -> 1080x1440 双色 PNG，<=20KB（超大时加强去噪/去膨胀）。"""
    for min_px, dil in ((5, 1), (10, 1), (16, 0), (24, 0)):
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
        if dst.stat().st_size <= LIMIT:
            return dst.stat().st_size, float(ink.mean()), (min_px, dil)
    return dst.stat().st_size, float(ink.mean() if False else 0.0), (24, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--budget", type=float, default=BUDGET)
    ap.add_argument("--chair", action="store_true")
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    ledger_path = HERE / "_all-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"runs": []}
    done = {r["pose"] for r in ledger["runs"] if r.get("ok")}
    spent = sum(r.get("price", 0) for r in ledger["runs"] if r.get("ok"))

    ids = args.ids or [p for p in ORDER if p not in SKIP]
    if args.resume:
        ids = [p for p in ids if p not in done]
    CHAIR_IDS = {k for k, v in SPECS.items() if v.get("chair")}
    prompt = BASE
    if args.chair:
        prompt = BASE.replace(
            "画面避免：",
            "参考图中的浅灰色块是坐具（椅子），请把它画成两三根极简线条构成的椅子，"
            "并让人物如实坐在椅子上（臀部接触椅面、双脚落地），不得把人物画成站立。画面避免：", 1)
    BACK_IDS = {k for k, v in SPECS.items() if v.get("view") == "back"}
    TOP_IDS = {"HOME-03", "HOME-07"}
    CHAIR_IDS = {k for k, v in SPECS.items() if v.get("chair")}

    def build_prompt(pid, force_chair=False, fix=False):
        add = []
        if pid in CHAIR_IDS or force_chair:
            add.append("参考图中的浅灰色块是坐具（椅子），请把它画成两三根极简线条构成的椅子，"
                       "并让人物如实坐在椅子上（臀部接触椅面、双脚落地），不得把人物画成站立。")
        if pid in BACK_IDS:
            add.append("参考图是背影视角（看不到五官），必须保持人物背面朝向镜头：画出后脑与发型的背面、"
                       "肩胛与背部线条、臀部与腿后侧，不得画成正面对镜头的站姿，不得出现五官与正脸。")
        if pid in TOP_IDS:
            add.append("这是正上方垂直俯拍的视角：人物平躺在床上/地面上，镜头从正上方看向人体，"
                       "画面里是俯视投影（头在上、脚在下，四肢向两侧摊开），身体是水平的，"
                       "不得画成站立姿势，不得出现地面接触面积过小的站姿。")
        if fix:
            add.append("手臂与手部动作必须与参考图一致：肘部弯曲角度、手部所在高度（脸前/胸前/体侧）"
                       "不得自行拉直、放下或改成对称姿势；手必须画出来，不得被躯干或头吞掉。")
        if not add:
            return BASE
        return BASE.replace("画面避免：", "".join(add) + "画面避免：", 1)

    env = ark_env()
    print(f"计划 {len(ids)} 张，已花 {spent:.2f} 元，预算 {args.budget:.2f} 元", flush=True)

    for pid in ids:
        ctrl = HERE / "_ctl" / f"{pid}.png"
        if not ctrl.exists():
            print(f"[{pid}] 缺控制图，跳过", flush=True)
            continue
        if spent + PRICE > args.budget + 1e-9:
            print(f"⛔ 预算到顶（{spent:.2f}/{args.budget:.2f}），停", flush=True)
            break
        p_prompt = build_prompt(pid, force_chair=args.chair, fix=args.fix)
        payload = {
            "model": MODEL, "prompt": p_prompt, "size": SIZE, "watermark": False,
            "output_format": "jpeg", "response_format": "url", "seed": seed_of(pid),
            "image": data_uri(ctrl),
        }
        if args.dry_run:
            print(f"[{pid}] seed={payload['seed']} ctl={ctrl.stat().st_size//1024}KB")
            continue
        cmd = ["arkcli", "api", "arkruntime.generate_images", "--profile", PROFILE,
               "--params", json.dumps(payload, ensure_ascii=False)]
        print(f"[{pid}] …", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"    ✗ exit={r.returncode} {r.stderr.strip()[:300]}", flush=True)
            ledger["runs"].append(dict(pose=pid, ok=False, error=r.stderr.strip()[:500],
                                       at=datetime.now().isoformat(timespec="seconds")))
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
            continue
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            print(f"    ✗ 非 JSON {r.stdout[:200]}", flush=True)
            continue
        url = find_url(data)
        if not url:
            print(f"    ✗ 无 URL {json.dumps(data, ensure_ascii=False)[:300]}", flush=True)
            ledger["runs"].append(dict(pose=pid, ok=False,
                                       error=json.dumps(data, ensure_ascii=False)[:500],
                                       at=datetime.now().isoformat(timespec="seconds")))
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
            continue
        spent += PRICE
        raw = HERE / "raw" / f"{pid}.jpg"
        raw.parent.mkdir(exist_ok=True)
        subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(raw), url],
                       capture_output=True, timeout=150)
        dst = HERE / f"{pid}.png"
        if dst.exists():
            (HERE / "_prev").mkdir(exist_ok=True)
            subprocess.run(["cp", str(dst), str(HERE / "_prev" / f"{pid}.png")])
        ok = raw.exists() and raw.stat().st_size > 0
        size, inkr, prm = (0, 0.0, ())
        if ok:
            size, inkr, prm = finish(raw, dst)
        ledger["runs"].append(dict(
            pose=pid, ok=ok, seed=payload["seed"], model=MODEL, size=SIZE, price=PRICE,
            file=raw.name, out=dst.name, out_bytes=size, ink_ratio=round(inkr, 4),
            post=prm, latency_s=round(time.time() - t0, 1), spent=round(spent, 2),
            at=datetime.now().isoformat(timespec="seconds")))
        ledger["spent"] = round(spent, 2)
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
        print(f"    {'✓' if ok else '✗'} {dst.name} {size/1024:.1f}KB "
              f"({time.time()-t0:.0f}s) 累计 {spent:.2f} 元", flush=True)

    print(f"结束：花费 {spent:.2f} 元，成功 {sum(1 for r in ledger['runs'] if r.get('ok'))} 张",
          flush=True)


if __name__ == "__main__":
    main()
