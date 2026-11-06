#!/usr/bin/env python3
"""ST 线稿试点驱动：两条路线各出对照图 + 记录台账

路线 A（骨架控制 i2i）：把 gen_skeleton.py 产出的白底骨架 raster 作为 image 控制图，
   交给 seedream 只负责"上风格"，姿态由骨架锁定。
路线 B（纯 AI 直出）：不给控制图，纯文本描述姿势，全凭模型理解。

通道：arkcli api arkruntime.generate_images（raw action，模型名直调；本账号 platform
数据面无 EP，+gen 传模型名会被客户端拦截）。params 全部内联 JSON，绝不 @file。

用法：
  python3 run_pilot.py --route A --ids ST-01
  python3 run_pilot.py --route B --ids ST-01
  python3 run_pilot.py --route A --ids ST-02 ST-03 ... --batch st-final
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

HERE = Path(__file__).resolve().parent
MODEL = "doubao-seedream-5-0-flash-260915"
PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"           # 3:4，总像素 3.98M（seedream 下限之上），落地再缩到 1080x1440
PRICE = 0.12                 # 元/张（目录折后价，结算以 T+1 billing 为准）

# 路线 A：骨架 -> 风格化线稿（骨架已给姿态，AI 只买"好看"）
PROMPT_A = (
    "将参考图中的人体骨架示意图重绘为杂志风时装速写线稿：单色深炭灰墨线，"
    "线条粗细均匀、收笔利落，在骨架基础上补出完整人体轮廓与主要结构线，"
    "不画阴影、不画排线、不画面料纹理，纯白背景，关节处保留实心小圆点，"
    "人物为年轻女性，全身站姿与参考图完全一致，竖构图，头顶与脚下留白，人物居中。"
    "画面避免：灰阶过渡、铅笔颗粒、文字、数字、标注、箭头、边框、多余线条、背景环境。"
)

# 路线 A v2（批量定版）：把 ST-01 试跑**意外产出**的服装锁死，最大化跨图一致性。
# 唯一改动：明确"连体练功服 + 简洁平底鞋 + 全身完整不裁切 + 禁外套/花纹/道具"。
PROMPT_A2 = (
    "将参考图中的人体骨架示意图重绘为杂志风时装速写线稿：单色深炭灰墨线，"
    "线条粗细均匀、收笔利落，在骨架基础上补出完整人体轮廓与主要结构线，"
    "不画阴影、不画排线、不画面料纹理，纯白背景，关节处保留实心小圆点，"
    "人物为年轻女性，穿贴身纯色连体练功服、线条简洁的平底鞋，发型简洁，"
    "全身姿态与参考图完全一致，竖构图，头顶与脚下留白，人物居中，全身完整入画不裁切。"
    "画面避免：灰阶过渡、铅笔颗粒、文字、数字、标注、箭头、边框、多余线条、背景环境、"
    "道具、外套、图案花纹。"
)

# 路线 B：纯文本直出（无控制图），把姿势语义写进提示词
PROMPT_B = (
    "一张杂志风时装速写线稿：单色深炭灰墨线，线条粗细均匀、收笔利落，"
    "只画轮廓与主要结构线，不画阴影、不画排线、不画面料纹理，纯白背景。"
    "人物：一位年轻女性全身站姿，双脚前后错开呈丁字步，重心落在后腿，"
    "双手自然下垂并微微离开身体，肩线放松下沉，头部正视前方，表情平静。"
    "竖构图全身，人物居中，头顶与脚下留白，身体主要关节处用实心小圆点标示。"
    "画面避免：灰阶过渡、铅笔颗粒、文字、数字、标注、箭头、边框、背景环境、环境道具。"
)


def seed_of(pid: str) -> int:
    """seed = md5(POSE-ID) mod 2^31 —— 与全库 seed 策略一致，可复现。"""
    return int(hashlib.md5(pid.encode()).hexdigest()[:8], 16) % 2147483647


def ark_env() -> dict:
    env = dict(os.environ)
    env.update(
        HOME="/var/folders/w0/2mw6jbm53fxbkgds_6d3504c0000gp/T/arkcli-poseguide-home",
        ARKCLI_NO_UPDATE_NOTIFIER="1",
        ARKCLI_CALLER_TYPE="ai_agent",
        ARKCLI_CALLER_NAME="dsh-takephoto-main",
        ARKCLI_SKILL_NAME="arkcli-gen",
    )
    return env


def data_uri(path: Path) -> str:
    b = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{b}"


def find_url(obj):
    """优先 d['data'][0]['url']，兜底递归找 http url。"""
    if isinstance(obj, dict):
        d = obj.get("data")
        if isinstance(d, list) and d and isinstance(d[0], dict) and d[0].get("url"):
            return d[0]["url"]
        for k, v in obj.items():
            if k in ("url", "output_url") and isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            u = find_url(v)
            if u:
                return u
    elif isinstance(obj, list):
        for v in obj:
            u = find_url(v)
            if u:
                return u
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", choices=["A", "B"], required=True)
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--batch", default="trial")
    ap.add_argument("--prompt", default=None, choices=["A", "A2", "B"],
                    help="提示词版本；缺省 A->PROMPT_A, A2->PROMPT_A2, B->PROMPT_B")
    ap.add_argument("--extra", default=None,
                    help="逐姿势的四肢动作补强语（写在『画面避免』之前），用于修复图片控制被模型抹平的姿势")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out_dir = HERE / args.batch
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = HERE / "_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"runs": []}
    env = ark_env()

    spent = 0.0
    for pid in args.ids:
        seed = seed_of(pid)
        if args.prompt:
            prompt = {"A": PROMPT_A, "A2": PROMPT_A2, "B": PROMPT_B}[args.prompt]
        else:
            prompt = PROMPT_A if args.route == "A" else PROMPT_B
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "size": SIZE,
            "watermark": False,
            "output_format": "jpeg",
            "response_format": "url",
            "seed": seed,
        }
        if args.extra:
            prompt = prompt.replace("画面避免", args.extra + "画面避免", 1)
        if args.route == "A":
            sk = HERE / f"_skeleton-ai-{pid}.png"
            if not sk.exists():
                sys.exit(f"缺少骨架控制图 {sk}")
            payload["image"] = data_uri(sk)

        if args.dry_run:
            brief = {k: (f"<base64 {len(payload[k])} chars>" if k == "image" else v)
                     for k, v in payload.items()}
            print(f"[{pid}] route={args.route} {json.dumps(brief, ensure_ascii=False)[:300]}")
            continue

        cmd = ["arkcli", "api", "arkruntime.generate_images", "--profile", PROFILE,
               "--params", json.dumps(payload, ensure_ascii=False)]
        print(f"[{pid}] route={args.route} seed={seed} …", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"    ✗ exit={r.returncode} {r.stderr.strip()[:500]}")
            ledger["runs"].append(dict(pose=pid, route=args.route, batch=args.batch,
                                       ok=False, error=r.stderr.strip()[:800],
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
            ledger["runs"].append(dict(pose=pid, route=args.route, batch=args.batch, ok=False,
                                       error=json.dumps(data, ensure_ascii=False)[:800],
                                       at=datetime.now().isoformat(timespec="seconds")))
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
            continue

        spent += PRICE
        target = out_dir / f"raw-{pid}-{args.route}.jpg"
        # 系统 python urllib 在 macOS 缺 CA 会 SSL 失败（已实测），改用 curl
        dl = subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(target), url],
                            capture_output=True, text=True, timeout=150)
        ok = dl.returncode == 0 and target.exists() and target.stat().st_size > 0
        print(f"    {'✓' if ok else '✗'} {target.name} "
              f"{target.stat().st_size if target.exists() else 0}B "
              f"({time.time() - t0:.0f}s)")
        ledger["runs"].append(dict(
            pose=pid, route=args.route, batch=args.batch, ok=ok, seed=seed, model=MODEL,
            size=SIZE, price=PRICE, file=target.name if ok else None, output_url=url,
            prompt=prompt, at=datetime.now().isoformat(timespec="seconds"),
            latency_s=round(time.time() - t0, 1),
        ))
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")

    total = sum(r.get("price", 0) for r in ledger["runs"] if r.get("ok"))
    print(f"\n本批 {len(args.ids)} 张 → {out_dir}；累计已花费 ≈ {total:.2f} 元")


if __name__ == "__main__":
    main()
