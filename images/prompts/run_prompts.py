#!/usr/bin/env python3
"""摆拍手册 PoseGuide · 示例图生成驱动脚本（可复跑）

数据源：images/prompts/pose-prompts-100.json（100 条提示词清单）
通道（默认 raw）：arkcli api arkruntime.generate_images —— 方舟同步图片生成 API，模型名直接调用。
  说明：本账号 platform 数据面仅接受 ep-* 接入点（`+gen` 传模型名会被客户端拦截），
  账号当前无已部署 EP，故默认走文档注册的 raw action；有 EP 的账号可用 --channel gen。
前置条件：模型已开通且未触发「安全体验模式」用量暂停（若报
  "reached the set usage limit ... Safe Experience Mode"，需账号所有人在方舟控制台
  模型开通页调整/关闭安全体验模式后重跑本脚本）。
台账：images/manifest.json（增量写入：姿势ID、路径、提示词、模型、种子、日期、sha256）

用法：
  python3 run_prompts.py --pilot            # 试点 10 张（清单中 pilot:true）
  python3 run_prompts.py --ids ST-02 DUO-04 # 指定姿势
  python3 run_prompts.py --all              # 全量 100 张（须用户确认规模与模型后再跑）
  python3 run_prompts.py --pilot --dry-run  # 只打印命令不执行
  可选：--model doubao-seedream-5-0-flash-260915（0.12元/张）
        --channel gen --endpoint ep-xxx（有接入点的账号）
        --seed-offset 1 --out-dir images/pilot --no-seed

模型备忘（2026-10-28 查证）：
  - doubao-seedream-5-0-pro   260628  现役旗舰   0.3 元/张  支持 seed/watermark
  - doubao-seedream-5-0-flash 260915  现役快速   0.12 元/张 支持 seed/watermark
  - doubao-seedream-4-5 / 5-0(lite) / 4-0   服务端返回 retiring，无法开通（其免费额度已不可用）
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

PROMPTS_FILE = Path(__file__).resolve().parent / "pose-prompts-100.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = PROJECT_ROOT / "images"
MANIFEST = IMAGES_DIR / "manifest.json"

DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"
DEFAULT_PROFILE = "platform_cn-beijing_accountwide"
SIZE = "1728x2304"  # 竖幅 3:4；5.0-pro 总像素区间 [921600, 4624220] 覆盖

# 目录单价（元/张，models get 返回的账号折后价；结算以 T+1 billing 为准）
PRICE_MAP = {
    "doubao-seedream-5-0-pro-260628": 0.3,
    "doubao-seedream-5-0-flash-260915": 0.12,
}


def ark_env(sandbox_home: bool) -> dict:
    env = dict(os.environ)
    env.update(
        ARKCLI_NO_UPDATE_NOTIFIER="1",
        ARKCLI_CALLER_TYPE="ai_agent",
        ARKCLI_CALLER_NAME="unknown_agent",
        ARKCLI_SKILL_NAME="arkcli-gen",
    )
    if sandbox_home:
        # 沙箱环境：主目录不可写，arkcli 状态迁移需要写 HOME。
        # 重定向到平台临时区的准备目录（其中已完成状态迁移并持有登录态）。
        th = Path(tempfile.gettempdir()) / "arkcli-poseguide-home"
        if not th.exists():
            sys.exit(f"sandbox home {th} 不存在：请先在该 HOME 下完成 arkcli 登录状态迁移")
        env["HOME"] = str(th)
    return env


def load_poses():
    data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    return data["meta"], {p["id"]: p for p in data["poses"]}


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"meta": {}, "records": []}


def save_manifest(m):
    m.setdefault("meta", {}).update(
        project="摆拍手册 PoseGuide · 示例图台账",
        prompt_source="images/prompts/pose-prompts-100.json",
        run_script="images/prompts/run_prompts.py",
        naming="{POSE-ID}.jpg",
        default_model=DEFAULT_MODEL,
        channel="arkcli api arkruntime.generate_images（模型名直接调用）",
        profile=DEFAULT_PROFILE,
        size=SIZE,
        aspect="3:4",
        watermark=False,
        output_format="jpeg",
        ai_generated=True,
        seed_policy="md5(POSE-ID) mod 2^31（--seed-offset 叠加；5.0-pro/flash 支持 seed 固定复现）",
    )
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_url(obj):
    if isinstance(obj, dict):
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


def gen_raw(p, model, profile, seed, env):
    payload = {
        "model": model,
        "prompt": p["prompt"],
        "size": SIZE,
        "watermark": False,
        "output_format": "jpeg",
        "response_format": "url",
    }
    if seed is not None:
        payload["seed"] = seed
    cmd = ["arkcli", "api", "arkruntime.generate_images",
           "--profile", profile, "--params", json.dumps(payload, ensure_ascii=False)]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    return cmd, r


def gen_plus(p, model, profile, seed, env):
    tmp_dir = Path(tempfile.mkdtemp(prefix="posegen-"))
    cmd = ["arkcli", "+gen", "--model", model, "--profile", profile,
           "--modality", "image", "--size", SIZE, "--watermark=false",
           "--format", "json", "--no-open", f"--save-to={tmp_dir}"]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    cmd.append(p["prompt"])
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    local = None
    if r.returncode == 0 and r.stdout.strip():
        d = json.loads(r.stdout)
        local = d.get("local_path") or (d.get("local_paths") or [None])[0]
    return cmd, r, local


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pilot", action="store_true", help="生成清单中 pilot:true 的 10 张")
    g.add_argument("--ids", nargs="+", help="指定姿势 ID")
    g.add_argument("--all", action="store_true", help="全量 100 张（确认规模与模型后使用）")
    ap.add_argument("--model", default=None, help="统一覆盖模型；缺省用清单逐条 model 字段（混合方案）")
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    ap.add_argument("--channel", choices=["raw", "gen"], default="raw")
    ap.add_argument("--endpoint", default=None, help="--channel gen 时的 ep-*（覆盖 --model 语义）")
    ap.add_argument("--out-dir", default=None, help="输出目录（默认 images/pilot，--all 时 images/）")
    ap.add_argument("--name-with-model", action="store_true", help="文件名含模型名：{ID}_{model}.jpg")
    ap.add_argument("--seed-offset", type=int, default=0)
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--sandbox-home", action="store_true", help="重定向 HOME 到沙箱准备目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的命令与参数，不联网")
    args = ap.parse_args()

    meta, poses = load_poses()
    if args.pilot:
        selected = [p for p in poses.values() if p.get("pilot")]
        out_dir = IMAGES_DIR / "pilot"
    elif args.ids:
        missing = [i for i in args.ids if i not in poses]
        if missing:
            sys.exit(f"未知姿势 ID：{missing}")
        selected = [poses[i] for i in args.ids]
        out_dir = IMAGES_DIR / "pilot"
    else:
        selected = list(poses.values())
        out_dir = IMAGES_DIR
    if args.out_dir:
        out_dir = PROJECT_ROOT / args.out_dir

    # 模型解析优先级：--endpoint > 显式 --model > 清单逐条 model 字段 > DEFAULT_MODEL
    def resolve_model(p):
        return args.endpoint or args.model or p.get("model") or DEFAULT_MODEL

    status_label = "pilot" if out_dir != IMAGES_DIR else "final"
    used = sorted({resolve_model(p) for p in selected})
    print(f"选中 {len(selected)} 条 → 输出 {out_dir}（status={status_label}，channel={args.channel}）")
    print(f"涉及模型：{', '.join(used)}\n")

    manifest = load_manifest()

    def record_key(r):
        # 复合键：同一姿势可能有多条记录（compare 双模型、lost、主产线），避免互相覆盖
        return f"{r.get('pose_id')}|{r.get('model', '')}|{r.get('purpose') or 'main'}"

    records_by_id = {record_key(r): r for r in manifest.get("records", [])}
    env = ark_env(args.sandbox_home)
    ok, fail = 0, 0

    for p in selected:
        seed = None if args.no_seed else (p["seed"] + args.seed_offset) % 2147483647
        model = resolve_model(p)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / (f"{p['id']}_{model}.jpg" if args.name_with_model else f"{p['id']}.jpg")

        if args.dry_run:
            payload = {"model": model, "prompt": p["prompt"][:40] + "…", "size": SIZE,
                       "seed": seed, "watermark": False, "output_format": "jpeg"}
            print(f"[{p['id']}] arkcli api arkruntime.generate_images --params {json.dumps(payload, ensure_ascii=False)}")
            continue

        print(f"[{p['id']}] 生成中（model={model}, seed={seed}）…")
        local = None
        if args.channel == "raw":
            cmd, r = gen_raw(p, model, args.profile, seed, env)
            if r.returncode != 0:
                print(f"    ✗ exit={r.returncode}\n    stderr: {r.stderr.strip()[:400]}")
                if "Safe Experience Mode" in r.stderr or "usage limit" in r.stderr:
                    print("    ⚠️ 账号安全体验模式用量上限已触发：请在方舟控制台「模型开通页」调整/关闭后重跑本脚本。")
                    break  # 同一账号级阻断，后续必然同样失败，停止省时
                fail += 1
                continue
            try:
                data = json.loads(r.stdout)
            except json.JSONDecodeError:
                print(f"    ✗ 输出非 JSON：{r.stdout[:200]}")
                fail += 1
                continue
            url = find_url(data)
            if not url:
                print(f"    ✗ 未找到图片 URL：{json.dumps(data, ensure_ascii=False)[:300]}")
                fail += 1
                continue
            try:
                # 用 curl 下载：系统 python 的 urllib 在 macOS 缺 CA 证书会 SSL 验证失败（已实测踩坑）
                dl = subprocess.run(["curl", "-sSfL", "--max-time", "120", "-o", str(target), url],
                                    capture_output=True, text=True, timeout=150)
                if dl.returncode != 0 or not target.exists() or target.stat().st_size == 0:
                    raise RuntimeError(f"curl rc={dl.returncode} {dl.stderr[:150]}")
            except Exception as e:  # noqa: BLE001 —— 下载失败保留 URL 待人工抢救（24h 有效）
                print(f"    ⚠️ 下载失败（URL 已记录，24h 内有效）：{e}")
                records_by_id[f"{p['id']}|{model}|main"] = {
                    "pose_id": p["id"], "pose_name": p["name"], "category": p["category"],
                    "file": None, "output_url": url, "model": model, "seed": seed,
                    "date": date.today().isoformat(), "size": SIZE, "aspect": "3:4",
                    "watermark": False, "ai_generated": True, "status": "url_only", "qa": "pending",
                }
                manifest["records"] = list(records_by_id.values())
                save_manifest(manifest)
                fail += 1
                continue
        else:
            cmd, r, local = gen_plus(p, model, args.profile, seed, env)
            if r.returncode != 0 or not local or not Path(local).exists():
                print(f"    ✗ exit={r.returncode} stderr={r.stderr.strip()[:300]}")
                fail += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(local, target)

        rec = {
            "pose_id": p["id"], "pose_name": p["name"], "category": p["category"],
            "file": str(target.relative_to(PROJECT_ROOT)),
            "prompt_chars": len(p["prompt"]), "prompt_id": p["id"],
            "model": model, "seed": seed, "date": date.today().isoformat(),
            "size": SIZE, "aspect": "3:4", "watermark": False, "ai_generated": True,
            "status": status_label,
            "catalog_price_cny": PRICE_MAP.get(model),
            "sha256": sha256(target), "qa": "pending",
        }
        records_by_id[f"{p['id']}|{model}|main"] = rec
        manifest["records"] = list(records_by_id.values())
        save_manifest(manifest)
        print(f"    ✓ {target.name}（sha256 前 8 位={rec['sha256'][:8]}）")
        ok += 1

    if not args.dry_run:
        save_manifest(manifest)
        print(f"\n完成：成功 {ok}，失败 {fail}；台账 → {MANIFEST}")
    else:
        print(f"\ndry-run 共 {len(selected)} 条")


if __name__ == "__main__":
    main()
