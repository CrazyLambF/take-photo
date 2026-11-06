#!/usr/bin/env python3
"""模特统一重出：38 张非主设定单人图，带 REF-STANDARD 参考图。
用法: python3 run_unify.py <ref_small.jpg>
前置: 环境变量 HOME 已指向 arkcli 沙箱 HOME（登录态就绪）。
预算护栏: 付费调用上限 44（38 张 + 6 次重试）。
"""
import base64, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # images/
PROJ = ROOT.parent                                      # 项目根
PROMPTS_FILE = ROOT / "prompts" / "pose-prompts-100.json"
MANIFEST = ROOT / "manifest.json"
ARCHIVE = ROOT / "archive-v1"
SIZE = "1728x2304"
PROFILE = "platform_cn-beijing_accountwide"
MAX_CALLS = 44
OLD_CLAUSE = "深棕色齐肩短发，圆脸元气笑容"
NEW_CLAUSE = "黑色长直发，气质温柔干净"

REDO = ['ST-03','ST-04','ST-06','ST-07','ST-08','SIT-01','SIT-03','SIT-05','SIT-07','SIT-09',
'STREET-01','STREET-02','STREET-04','STREET-05','STREET-07','STREET-09',
'TRAVEL-01','TRAVEL-04','TRAVEL-07','TRAVEL-09','TRAVEL-10','HOME-02','HOME-04','HOME-06','HOME-07',
'CAFE-01','CAFE-03','CAFE-07','CLOSE-02','CLOSE-04','CLOSE-05','CLOSE-10',
'PROP-02','PROP-03','PROP-05','PROP-07','PROP-09','PROP-10']


def ark_env():
    env = dict(os.environ)
    env.update(ARKCLI_NO_UPDATE_NOTIFIER="1", ARKCLI_CALLER_TYPE="ai_agent",
               ARKCLI_CALLER_NAME="dsh-takephoto-main", ARKCLI_SKILL_NAME="arkcli-gen")
    return env


def data_url(ref_path: str) -> str:
    b64 = base64.b64encode(Path(ref_path).read_bytes()).decode()
    return "data:image/jpeg;base64," + b64


def gen_one(model, prompt, seed, ref_url, env):
    params = {"model": model, "prompt": prompt, "image": [ref_url], "size": SIZE,
              "watermark": False, "output_format": "jpeg", "response_format": "url",
              "seed": seed}
    r = subprocess.run(["arkcli", "api", "arkruntime.generate_images",
                        "--profile", PROFILE, "--params", json.dumps(params, ensure_ascii=False)],
                       env=env, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if "state_migration" in out or "operation not permitted" in out:
        print("FATAL: arkcli 环境异常（状态迁移失败），停止全部后续调用", flush=True)
        sys.exit(2)
    if r.returncode != 0:
        return None, out[:300]
    try:
        d = json.loads(r.stdout)
        return d["data"][0]["url"], None
    except Exception as e:
        return None, f"parse: {e}: {(r.stdout + r.stderr)[:200]}"


def download(url, dest: Path):
    r = subprocess.run(["curl", "-sS", url, "-o", str(dest)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not dest.exists() or dest.stat().st_size < 50000:
        return f"download fail: rc={r.returncode} size={dest.stat().st_size if dest.exists() else 0}"
    return None


def verify_jpg_size(dest: Path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(dest)],
                       capture_output=True, text=True)
    return "1728" in r.stdout and "2304" in r.stdout


def main():
    ref_small = sys.argv[1]
    ref_url = data_url(ref_small)
    env = ark_env()
    data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    poses = {p["id"]: p for p in data["poses"]}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recs = {r["pose_id"]: r for r in manifest["records"]}
    ARCHIVE.mkdir(exist_ok=True)
    tmp = Path(os.environ.get("TMPDIR", "/tmp"))

    calls, ok, fails = 0, 0, []
    for i, pid in enumerate(REDO, 1):
        pose = poses[pid]
        rec = recs[pid]
        prompt = pose["prompt"]
        if OLD_CLAUSE in prompt:
            prompt = prompt.replace(OLD_CLAUSE, NEW_CLAUSE)
        else:
            fails.append((pid, "clause-miss"))  # 不应发生；保守跳过避免错生成
            print(f"[{i}/38] {pid} SKIP: 人物子句不匹配", flush=True)
            continue
        dest = PROJ / rec["file"]
        archive_path = ARCHIVE / dest.name
        result, last_err = None, None
        for attempt in (1, 2, 3):
            if calls >= MAX_CALLS:
                print("BUDGET-STOP", flush=True)
                break
            calls += 1
            url, err = gen_one(pose["model"], prompt, pose["seed"], ref_url, env)
            if not url:
                last_err = err
                print(f"[{i}/38] {pid} call{calls} err: {last_err}", flush=True)
                time.sleep(3)
                continue
            tmp_img = tmp / f"unify-{pid}.jpg"
            err = download(url, tmp_img)
            if err or not verify_jpg_size(tmp_img):
                last_err = err or "size-mismatch"
                print(f"[{i}/38] {pid} verify err: {last_err}", flush=True)
                tmp_img.unlink(missing_ok=True)
                time.sleep(3)
                continue
            if dest.exists():
                shutil.move(str(dest), str(archive_path))
            shutil.move(str(tmp_img), str(dest))
            rec["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
            rec["date"] = "2026-10-29"
            rec["qa"] = {"verdict": "pending", "notes": "unify rework 待QA", "qa_by": "coordinator"}
            rec["unify_rework"] = {"date": "2026-10-29", "ref": "images/test/REF-STANDARD.jpg"}
            manifest["records"] = [r for r in manifest["records"] if r["pose_id"] != pid] + [rec]
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            result = True
            break
        if result:
            ok += 1
            print(f"[{i}/38] {pid} OK (calls={calls})", flush=True)
        elif pid not in [f[0] for f in fails]:
            fails.append((pid, last_err or "unknown"))
            print(f"[{i}/38] {pid} FAIL: {last_err}", flush=True)

    print(json.dumps({"ok": ok, "fail": len(fails), "calls": calls,
                      "failed_ids": [f[0] for f in fails]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
