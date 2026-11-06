#!/usr/bin/env python3
"""ST-04/05/09 体积人偶控制图复测（预算 0.36 元 = 3 张 × 0.12）

与 run_pilot.py 的唯一差别：
  1. image 控制图换成 _vol-ai-ST-xx.png（有体积人偶）
  2. 提示词把参考图称作"人体人偶"，并要求"把深灰实体块全部改为空心轮廓线"
  3. 硬闸：最多 3 次调用，超预算立即停

用法：
  python3 run_vol.py --ids ST-04 ST-05 ST-09 --variant base
  python3 run_vol.py --ids ST-04 --variant fix      # 文字补强（本轮预算内不跑）
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "doubao-seedream-5-0-flash-260915"
PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"
PRICE = 0.12           # 元/张（目录折后价；3 张 = 0.36 预算上限）
BUDGET = 0.36
MAX_CALLS = 3

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

# 文字补强版：只在"基础版失败"时用（本轮预算 0.36 只够 base，此处留档可复跑）
FIX = BASE.replace(
    "全身姿态与参考图完全一致",
    "手臂不得并入躯干轮廓、不得被躯干吞掉；双手插袋需画出手掌与胯部的接触关系；"
    "手臂上举或交叉时，肘部与手腕的朝向必须和参考图一致，不得自行放平。"
    "不得自行美化或修正姿态。全身姿态与参考图完全一致",
    1,
)


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
        for k, v in o.items():
            if k in ("url", "output_url") and isinstance(v, str) and v.startswith("http"):
                return v
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--variant", choices=["base", "fix"], default="base")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if len(args.ids) > MAX_CALLS:
        raise SystemExit(f"本批 {len(args.ids)} 张 > 预算上限 {MAX_CALLS} 张，拒绝执行")

    ledger_path = HERE / "_vol-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"runs": []}
    spent = sum(r.get("price", 0) for r in ledger["runs"] if r.get("ok"))
    env = ark_env()
    prompt = BASE if args.variant == "base" else FIX

    for pid in args.ids:
        ctrl = HERE / f"_vol-ai-{pid}.png"
        if not ctrl.exists():
            raise SystemExit(f"缺少控制图 {ctrl}（先跑 gen_mannequin.py）")
        if spent + PRICE > BUDGET + 1e-9:
            print(f"⛔ 已达预算上限 {BUDGET} 元（已花 {spent:.2f}），停止")
            break
        payload = {
            "model": MODEL, "prompt": prompt, "size": SIZE, "watermark": False,
            "output_format": "jpeg", "response_format": "url", "seed": seed_of(pid),
            "image": data_uri(ctrl),
        }
        if args.dry_run:
            brief = {k: (f"<base64 {len(v)} chars>" if k == "image" else v)
                     for k, v in payload.items()}
            print(f"[{pid}] {json.dumps(brief, ensure_ascii=False)[:400]}")
            continue
        cmd = ["arkcli", "api", "arkruntime.generate_images", "--profile", PROFILE,
               "--params", json.dumps(payload, ensure_ascii=False)]
        print(f"[{pid}] variant={args.variant} seed={payload['seed']} …", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"    ✗ exit={r.returncode} {r.stderr.strip()[:400]}")
            ledger["runs"].append(dict(pose=pid, variant=args.variant, ok=False,
                                       error=r.stderr.strip()[:600],
                                       at=datetime.now().isoformat(timespec="seconds")))
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
            continue
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            print(f"    ✗ 非 JSON：{r.stdout[:300]}")
            continue
        url = find_url(data)
        if not url:
            print(f"    ✗ 无 URL：{json.dumps(data, ensure_ascii=False)[:400]}")
            ledger["runs"].append(dict(pose=pid, variant=args.variant, ok=False,
                                       error=json.dumps(data, ensure_ascii=False)[:600],
                                       at=datetime.now().isoformat(timespec="seconds")))
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
            continue
        spent += PRICE
        target = HERE / f"_vol-raw-{pid}-{args.variant}.jpg"
        dl = subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(target), url],
                            capture_output=True, text=True, timeout=150)
        ok = dl.returncode == 0 and target.exists() and target.stat().st_size > 0
        print(f"    {'✓' if ok else '✗'} {target.name} "
              f"{target.stat().st_size if target.exists() else 0}B ({time.time() - t0:.0f}s)")
        ledger["runs"].append(dict(
            pose=pid, variant=args.variant, ok=ok, seed=payload["seed"], model=MODEL,
            size=SIZE, price=PRICE, file=target.name if ok else None, output_url=url,
            control=ctrl.name, prompt=prompt,
            at=datetime.now().isoformat(timespec="seconds"),
            latency_s=round(time.time() - t0, 1)))
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")

    total = sum(r.get("price", 0) for r in ledger["runs"] if r.get("ok"))
    print(f"\n本轮累计花费 ≈ {total:.2f} 元（预算 {BUDGET}）")


if __name__ == "__main__":
    main()
