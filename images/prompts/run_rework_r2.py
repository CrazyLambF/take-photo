#!/usr/bin/env python3
"""r2 比例返工：6 张全身照重出（用户反馈「几张全身照比例不协调」，协调者亲验确认 6 张）。
用法: python3 run_rework_r2.py <ref_small.jpg>
前置: 环境变量 HOME 已指向 arkcli 沙箱 HOME（登录态就绪）。
预算护栏: 付费调用上限 10（6 张目标 + 4 次重试）；环境级错误立即终止。
成功后动作: 旧图归档 images/archive-v1/{id}-pre-r2.jpg → 新图落位 images/{id}.jpg
          → manifest 记录更新并追加 rework 块 → pose-prompts-100.json 同步 prompt+seed。
种子: int(md5(f"{id}-r2").hexdigest()[:8], 16) % 2147483647（SCENE-10 与 11-02 已用 r2 种子重合，如实记录）。
"""
import base64, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path("images")
PROJ = Path(".")
PROMPTS_FILE = ROOT / "prompts" / "pose-prompts-100.json"
MANIFEST = ROOT / "manifest.json"
ARCHIVE = ROOT / "archive-v1"
SIZE = "1728x2304"
PROFILE = "platform_cn-beijing_accountwide"
MAX_CALLS = 10
DATE = "2026-11-03"
MODEL = "doubao-seedream-5-0-flash-260915"

ORDER = ["SCENE-10", "STREET-07", "BACK-03", "TRAVEL-03", "ST-10", "BACK-10"]

# 任务规定护栏（提示词原样含「人物占画面约 1/2」「头身比正常」；避免含「头身比例失调」「腿部拉长」）
CORE = ("人物占画面约 1/2（全身完整入镜），头身比正常（约1:7），四肢与躯干比例真实自然；"
        "画面避免：头身比例失调、腿部拉长、肢体畸形、手指畸形。")
EXTRA = {
    "SCENE-10": "行李箱为20寸登机箱大小，箱顶约到人物大腿中部。",
    "STREET-07": "单车各部件与人物身高比例真实，双脚自然着地或轻放踏板。",
    "BACK-03": "站姿腿长与躯干比例真实，双腿自然修长不缩短。",
    "TRAVEL-03": "双手五指自然张开，手指长短比例正常。",
    "ST-10": "手部五指自然放松，手指粗细长短比例正常。",
    "BACK-10": "跳跃中双腿自然弯曲，小腿与大腿比例真实。",
}
REASON = {
    "SCENE-10": "亲验右腿小腿视觉拉长、整体偏细长（该图 11-02 已做过一次 r2 比例修复，本次复验仍判定偏长）",
    "STREET-07": "低机位下双腿拉长、前脚掌点地姿势不自然、单车脚踏悬空位置怪",
    "BACK-03": "躯干偏长、腿显短，头身比不协调",
    "TRAVEL-03": "右手指关节拉长（蛛指感）",
    "ST-10": "剪影抬手手指细长如爪",
    "BACK-10": "跳跃伸展腿小腿偏长",
}


def r2_seed(pid: str) -> int:
    return int(hashlib.md5(f"{pid}-r2".encode()).hexdigest()[:8], 16) % 2147483647


def gen_one(model, prompt, seed, ref_url, env):
    params = {"model": model, "prompt": prompt, "image": [ref_url], "size": SIZE,
              "watermark": False, "output_format": "jpeg", "response_format": "url",
              "seed": seed}
    r = subprocess.run(["arkcli", "api", "arkruntime.generate_images",
                        "--profile", PROFILE, "--params", json.dumps(params, ensure_ascii=False)],
                       env=env, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if "state_migration" in out or "operation not permitted" in out or "profile" in out and "not found" in out:
        print("FATAL: arkcli 环境异常，停止全部后续调用", flush=True)
        print(out[:400], flush=True)
        sys.exit(2)
    if r.returncode != 0:
        return None, out[:300]
    try:
        d = json.loads(r.stdout)
        return d["data"][0]["url"], None
    except Exception as e:
        return None, f"parse: {e}: {out[:200]}"


def verify_jpg(dest: Path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(dest)],
                       capture_output=True, text=True)
    return "1728" in r.stdout and "2304" in r.stdout


def main():
    ref_url = "data:image/jpeg;base64," + base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
    env = dict(os.environ)
    env.update(ARKCLI_NO_UPDATE_NOTIFIER="1", ARKCLI_CALLER_TYPE="ai_agent",
               ARKCLI_CALLER_NAME="dsh-takephoto-main", ARKCLI_SKILL_NAME="arkcli-gen")
    data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    pose_by_id = {p["id"]: p for p in data["poses"]}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tmp = Path(os.environ.get("TMPDIR", "/tmp"))

    calls, ok, fails = 0, 0, []
    reworked = []
    for pid in ORDER:
        pose = pose_by_id[pid]
        base_prompt = pose["prompt"]
        new_prompt = base_prompt + EXTRA[pid] + CORE
        seed = r2_seed(pid)
        old_rec = next((r for r in manifest["records"] if r["pose_id"] == pid), {})
        dest = PROJ / "images" / f"{pid}.jpg"
        if not dest.exists():
            fails.append(pid)
            print(f"{pid} FAIL: 旧图不存在", flush=True)
            continue
        old_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        old_seed = old_rec.get("seed")

        result, last_err = None, None
        while calls < MAX_CALLS:
            calls += 1
            url, err = gen_one(MODEL, new_prompt, seed, ref_url, env)
            if not url:
                last_err = err
                print(f"{pid} call{calls} err: {last_err}", flush=True)
                time.sleep(3)
                continue
            tmp_img = tmp / f"r2-{pid}.jpg"
            r = subprocess.run(["curl", "-sS", url, "-o", str(tmp_img)], capture_output=True, timeout=120)
            if r.returncode != 0 or not tmp_img.exists() or tmp_img.stat().st_size < 50000 or not verify_jpg(tmp_img):
                last_err = "download/verify fail"
                print(f"{pid} call{calls} verify err: {last_err}", flush=True)
                tmp_img.unlink(missing_ok=True)
                time.sleep(3)
                continue
            # 成功：归档旧图 → 落位新图 → manifest + prompts 同步
            arch = ARCHIVE / f"{pid}-pre-r2.jpg"
            dest.replace(arch)
            tmp_img.replace(dest)
            new_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
            rec = dict(old_rec)
            rec.update({
                "file": f"images/{pid}.jpg",
                "prompt_chars": len(new_prompt),
                "prompt_id": "v1.2-r2-" + pid,
                "model": MODEL,
                "seed": seed,
                "date": DATE,
                "size": "1728x2304", "aspect": "3:4",
                "watermark": False, "ai_generated": True, "status": "final",
                "catalog_price_cny": 0.12,
                "sha256": new_sha,
                "qa": {"verdict": "pending",
                       "notes": f"r2 比例返工已出图，待协调者视觉复验；返工原因：{REASON[pid]}",
                       "qa_by": "image-prompt-engineer"},
            })
            rec["rework"] = {
                "round": "r2", "date": DATE,
                "reason": REASON[pid],
                "old_file": f"images/archive-v1/{pid}-pre-r2.jpg",
                "old_sha256": old_sha, "old_seed": old_seed,
                "guardrail": CORE, "cost_cny": 0.12,
            }
            manifest["records"] = [x for x in manifest["records"] if x["pose_id"] != pid] + [rec]
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            pose["prompt"] = new_prompt
            pose["seed"] = seed
            PROMPTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            reworked.append(pid)
            result = True
            print(f"{pid} OK seed={seed} prompt_chars={len(new_prompt)} (calls={calls})", flush=True)
            break
        if result:
            ok += 1
        else:
            fails.append(pid)
            print(f"{pid} FAIL: {last_err}", flush=True)

    if reworked:
        data["meta"]["r2_rework"] = {
            "date": DATE, "ids": reworked, "model": MODEL,
            "guardrail": CORE,
            "note": "用户反馈全身照比例不协调；协调者亲验 6 张确认后按 id-r2 种子重出，旧图归档 archive-v1/{id}-pre-r2.jpg",
        }
        PROMPTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": ok, "fail": len(fails), "calls": calls,
                      "reworked": reworked, "failed_ids": fails}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
