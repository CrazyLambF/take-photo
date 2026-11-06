#!/usr/bin/env python3
"""补做 20 条（上轮留空的坐姿/背影/遮挡类），硬预算 5.00 元。

沿用上轮定版技术参数：
  doubao-seedream-5-0-flash-260915 / 1728x2304 / watermark=false / seed=md5(ID)%2^31
  控制图 = 体块骨架（本次逐条修正几何后重绘，并加入支撑物：台阶/条椅/沙发/桌/床/堤沿）
  后处理 = #3B3630 / #F6F0E5 双色 + 膨胀 1px + <=20KB

两条已验证规律：
  1) 坐姿：控制图里把支撑物画出来 + 提示词明确「坐在…不是站立」-> 一次过
  2) 背影：提示词锁定「只有后脑/肩背/腿后侧，不出现正脸」

审核拒绝（input image may contain sensitive information）不重试，直接记为失败。
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_all as RA  # noqa: E402

MODEL = "doubao-seedream-5-0-flash-260915"
PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"
PRICE = 0.12
LIMIT = 20 * 1024
W, H = 1080, 1440

BASE = RA.BASE

# 每条：支撑物/动作补充说明（插在「画面避免：」之前）
EXTRA = {
    "SIT-03": "参考图中人物坐在一段台阶上：一条腿向前伸直、脚踩在台阶上，另一条腿屈膝、小腿交叉跨过伸直的腿；"
              "同侧手臂向后下方撑住台阶，上身略前倾、头微歪。台阶画成两三根极简直线构成的台沿。不得画成站立。",
    "SIT-04": "参考图中人物坐在草地上盘腿：双膝向身体一侧倒、两膝并拢，小腿在身前交叠盘起、脚掌收在腿下，"
              "双手撑在身体两侧的地面上。不得画成站立，不得画成坐椅子。",
    "SIT-05": "参考图中人物坐在高台阶/床沿的边沿上（不是站立）：双膝屈起贴近胸口，双脚踩在同一平面上，"
              "双臂向前环抱膝盖、小臂搭在膝前。台阶只画两三根极简直线。",
    "SIT-06": "人物半躺在沙发上：上身后靠在靠背上，一条腿伸展搭在沙发扶手上，另一条腿屈膝垂下，手臂放松。"
              "沙发只画座面、靠背、扶手三块极简轮廓。不得画成站立。",
    "SIT-07": "人物坐在地面上向后仰：双手在身体后侧撑地（手掌触地、手臂基本伸直），双腿向前伸展，"
              "腰线拉开、肩背放松。不得画成站立。",
    "SIT-08": "人物日式跪坐：双膝着地、小腿与脚背平贴地面，臀部坐在脚跟上，上身直立，双手交叠放在大腿上。"
              "不得画成站立或蹲。",
    "SIT-09": "人物反坐在椅子上：面朝椅背跨坐，双臂交叠伏在椅背顶端、下巴轻搁在手背上，双腿垂在椅子两侧。"
              "椅子只画极简线条（座面、椅背、四腿）。不得画成正坐或站立。",
    "BACK-05": "这是背影视角（看不到五官），必须保持背面朝向镜头：人物坐在天台/堤岸的边沿上，双腿自然垂向下方，"
               "一只手撑在身侧的边沿上。只画后脑与发型的背面、肩胛与背部、臀部与腿的后侧。"
               "不得画成正面对镜头的站姿，不得出现五官与正脸。",
    "BACK-06": "这是背影视角（看不到五官），必须保持背面朝向镜头：人物沿小路正中向前走，双臂自然前后摆动。"
               "只画后脑与发型的背面、肩胛与背部、臀部与腿的后侧。不得画成正脸，不得出现五官。",
    "HOME-02": "人物趴在床上：上身用小臂撑起、一只手托腮抬头，小腿向上翘起并在空中交叠晃动，身体接近水平。"
               "不得画成站立。",
    "HOME-04": "人物侧身站在台面前，肩背向镜头方向扭转、回头看镜头微笑，一只手在胸腹高度拿着东西。",
    "HOME-05": "人物对镜自拍：侧身站立，一只手把手机举到脸侧（手在脸部高度、手机挡住半张脸），"
               "另一只手扶在腰上，重心落在一侧。",
    "CAFE-04": "镜头在桌面高度：人物坐在桌前，两条小臂搁在桌面上朝镜头方向伸出（手在最前面），"
               "桌上放一只咖啡杯，上身微微前倾。桌子只画一条桌沿与两三条极简桌腿。",
    "PROP-01": "人物双手把一束花举到脸前，花束挡在下半张脸前，只露出眼睛与笑意。花束是唯一允许的道具，"
               "画成几根简洁的枝条与花朵轮廓。",
    "PROP-03": "人物举起手机自拍：一只手把手机举到脸侧前方、镜头朝向自己，另一只手自然放在身侧，"
               "低头看屏幕微笑。手机是唯一允许的道具。",
    "SCENE-05": "人物坐在海堤边沿抱膝：双膝屈起贴近胸口，双臂环抱膝盖，下巴靠近膝盖望向画外。"
                "堤沿只画一两根极简直线。不得画成站立。",
    "SCENE-08": "人物侧躺在野餐布上：一只手肘撑地托住头，另一只手放在身前，双腿并拢微屈，身体接近水平，"
                "视线看向镜头。不得画成站立。",
    "STREET-05": "人物伸手推开身前的店门：一只手臂向前伸出、手掌推在门板上，身体略前倾，另一只手自然下垂。"
                 "门只画一两条极简竖线。",
    "STREET-09": "人物蹲在路边：双膝深屈、臀部接近脚晎，一只手扶在膝盖上、另一只手伸向地面（像系鞋带），"
                 "上身略前倾。",
    "TRAVEL-05": "人物侧坐在沙滩上：一条腿屈膝、另一条腿略向前伸，一只手向后撑在沙面上，望向远处。"
                 "沙地只画一条极简横线。",
}
PROP_ALLOW = {"PROP-01", "PROP-03", "HOME-05", "CAFE-04"}

ORDER = ["SIT-03", "SIT-04", "SIT-05", "SIT-06", "SIT-07", "SIT-08", "SIT-09",
         "BACK-05", "BACK-06",
         "HOME-02", "HOME-04", "HOME-05", "TRAVEL-05", "STREET-05", "STREET-09",
         "PROP-01", "PROP-03", "SCENE-05", "SCENE-08", "CAFE-04"]


def build(pid):
    base = BASE
    if pid in PROP_ALLOW:
        base = base.replace("背景环境、道具、外套", "背景环境、外套")
    add = EXTRA[pid]
    return base.replace("画面避免：", f"【本条补充】{add}画面避免：", 1)


def ctl_of(pid):
    for d in ("_ctl2", "_ctl"):
        p = HERE / d / f"{pid}.png"
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=5.00)
    args = ap.parse_args()
    ids = args.ids or ORDER

    led_path = HERE / "_retry-ledger.json"
    led = json.loads(led_path.read_text()) if led_path.exists() else {"runs": []}
    spent = sum(r.get("price", 0) for r in led["runs"] if r.get("ok"))
    done = {r["pose"] for r in led["runs"] if r.get("ok")}
    env = RA.ark_env()
    print(f"计划 {len(ids)} 张（已完成 {len(done)}），已花 {spent:.2f}，预算 {args.budget:.2f}", flush=True)

    for pid in ids:
        if pid in done:
            print(f"[{pid}] 已完成，跳过", flush=True)
            continue
        ctl = ctl_of(pid)
        if ctl is None:
            print(f"[{pid}] 缺控制图，跳过", flush=True)
            continue
        if spent + PRICE > args.budget + 1e-9:
            print(f"⛔ 预算到顶 {spent:.2f}/{args.budget:.2f}", flush=True)
            break
        prompt = build(pid)
        payload = {"model": MODEL, "prompt": prompt, "size": SIZE, "watermark": False,
                   "output_format": "jpeg", "response_format": "url",
                   "seed": RA.seed_of(pid), "image": RA.data_uri(ctl)}
        if args.dry_run:
            print(f"[{pid}] ctl={ctl.parent.name} seed={payload['seed']} prompt={len(prompt)}字", flush=True)
            continue
        cmd = ["arkcli", "api", "arkruntime.generate_images", "--profile", PROFILE,
               "--params", json.dumps(payload, ensure_ascii=False)]
        print(f"[{pid}] 生成中…", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        rec = dict(pose=pid, at=datetime.now().isoformat(timespec="seconds"),
                   ctl=str(ctl.relative_to(HERE)), model=MODEL, price=PRICE)
        if r.returncode != 0:
            err = (r.stderr or r.stdout).strip()[:400]
            rec.update(ok=False, error=err)
            print(f"    ✗ 失败 {err[:160]}", flush=True)
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2) + "\n")
            continue
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            rec.update(ok=False, error="非 JSON 输出")
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2) + "\n")
            continue
        url = RA.find_url(data)
        if not url:
            rec.update(ok=False, error=json.dumps(data, ensure_ascii=False)[:400])
            print(f"    ✗ 无图 {json.dumps(data, ensure_ascii=False)[:200]}", flush=True)
            led["runs"].append(rec)
            led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2) + "\n")
            continue
        spent += PRICE
        raw = HERE / "raw" / f"{pid}.jpg"
        raw.parent.mkdir(exist_ok=True)
        subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(raw), url],
                       capture_output=True, timeout=150)
        dst = HERE / f"{pid}.png"
        size = inkr = 0
        prm = []
        ok = raw.exists() and raw.stat().st_size > 0
        if ok:
            size, inkr, prm = RA.finish(raw, dst)
        rec.update(ok=ok, seed=payload["seed"], out_bytes=size, ink_ratio=round(inkr, 4),
                   post=prm, latency_s=round(time.time() - t0, 1), spent=round(spent, 2))
        led["runs"].append(rec)
        led["spent"] = round(spent, 2)
        led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2) + "\n")
        print(f"    {'✓' if ok else '✗'} {dst.name} {size/1024:.1f}KB ({time.time()-t0:.0f}s) 累计 {spent:.2f} 元",
              flush=True)

    print(f"结束：花费 {spent:.2f} 元", flush=True)


if __name__ == "__main__":
    main()
