#!/usr/bin/env python3
"""SCENE 场景类目生成：10 张单人新场景图，带 REF-STANDARD 参考图（模特统一）。
用法: python3 run_scene.py <ref_small.jpg>
前置: 环境变量 HOME 已指向 arkcli 沙箱 HOME（登录态就绪）。
预算护栏: 付费调用上限 14（10 张 + 4 次重试）；环境级错误立即终止。
"""
import base64, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path("images")
PROJ = Path(".")
PROMPTS_FILE = ROOT / "prompts" / "pose-prompts-100.json"
MANIFEST = ROOT / "manifest.json"
SIZE = "1728x2304"
PROFILE = "platform_cn-beijing_accountwide"
MAX_CALLS = 14


def gen_one(model, prompt, seed, ref_url, env):
    params = {"model": model, "prompt": prompt, "image": [ref_url], "size": SIZE,
              "watermark": False, "output_format": "jpeg", "response_format": "url",
              "seed": seed}
    r = subprocess.run(["arkcli", "api", "arkruntime.generate_images",
                        "--profile", PROFILE, "--params", json.dumps(params, ensure_ascii=False)],
                       env=env, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if "state_migration" in out or "operation not permitted" in out:
        print("FATAL: arkcli 环境异常，停止全部后续调用", flush=True)
        sys.exit(2)
    if r.returncode != 0:
        return None, out[:300]
    try:
        d = json.loads(r.stdout)
        return d["data"][0]["url"], None
    except Exception as e:
        return None, f"parse: {e}: {out[:200]}"


def verify_jpg_size(dest: Path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(dest)],
                       capture_output=True, text=True)
    return "1728" in r.stdout and "2304" in r.stdout


def main():
    ref_url = "data:image/jpeg;base64," + base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
    env = dict(os.environ)
    env.update(ARKCLI_NO_UPDATE_NOTIFIER="1", ARKCLI_CALLER_TYPE="ai_agent",
               ARKCLI_CALLER_NAME="dsh-takephoto-main", ARKCLI_SKILL_NAME="arkcli-gen")
    data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    poses = [p for p in data["poses"] if p["category"] == "SCENE"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    have = {r["pose_id"] for r in manifest["records"]}
    tmp = Path(os.environ.get("TMPDIR", "/tmp"))

    calls, ok, fails = 0, 0, []
    for i, pose in enumerate(poses, 1):
        pid = pose["id"]
        result, last_err = None, None
        for attempt in (1, 2, 3):
            if calls >= MAX_CALLS:
                print("BUDGET-STOP", flush=True)
                break
            calls += 1
            url, err = gen_one(pose["model"], pose["prompt"], pose["seed"], ref_url, env)
            if not url:
                last_err = err
                print(f"[{i}/10] {pid} call{calls} err: {last_err}", flush=True)
                time.sleep(3)
                continue
            tmp_img = tmp / f"scene-{pid}.jpg"
            r = subprocess.run(["curl", "-sS", url, "-o", str(tmp_img)], capture_output=True, timeout=120)
            if r.returncode != 0 or not tmp_img.exists() or tmp_img.stat().st_size < 50000 or not verify_jpg_size(tmp_img):
                last_err = "download/verify fail"
                print(f"[{i}/10] {pid} verify err: {last_err}", flush=True)
                tmp_img.unlink(missing_ok=True)
                time.sleep(3)
                continue
            dest = PROJ / f"images/{pid}.jpg"
            tmp_img.replace(dest)
            rec = {
                "pose_id": pid, "pose_name": pose["name"], "category": "SCENE",
                "file": f"images/{pid}.jpg", "prompt_chars": len(pose["prompt"]),
                "prompt_id": "v1.1-" + pid, "model": pose["model"], "seed": pose["seed"],
                "date": "2026-10-29", "size": "1728x2304", "aspect": "3:4",
                "watermark": False, "ai_generated": True, "status": "final",
                "catalog_price_cny": 0.12,
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                "qa": {"verdict": "pending", "notes": "SCENE 新增待QA", "qa_by": "coordinator"},
                "scene_new": True,
                "ref_image": "images/test/REF-STANDARD.jpg",
            }
            manifest["records"] = [x for x in manifest["records"] if x["pose_id"] != pid] + [rec]
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            result = True
            break
        if result:
            ok += 1
            print(f"[{i}/10] {pid} OK (calls={calls})", flush=True)
        else:
            fails.append(pid)
            print(f"[{i}/10] {pid} FAIL: {last_err}", flush=True)

    print(json.dumps({"ok": ok, "fail": len(fails), "calls": calls, "failed_ids": fails},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
