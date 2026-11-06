#!/usr/bin/env python3
"""
用 MediaPipe PoseLandmarker 从 100 张封面提取真实关节坐标。

背景：程序化绘制的骨架与真实封面构图错位（叠加验证：SIT-01 骨架压在脸上、
STREET-01 偏右、BACK-01 手臂飘在空中），不能用于派生标注坐标。本脚本改为
对封面做真实姿态估计。

用法：
  PYTHONPATH=tools/pydeps MPLCONFIGDIR=$TMPDIR/mpl python3 tools/extract_joints.py

输出：images/lineart/joints-real.json
  坐标归一化 0–1，画幅 3:4。L/R 按「画面左 / 画面右」标注（已从 MediaPipe
  的人物自身左右翻转）。
"""
import json
import os

import numpy as np
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, 'tools/models/pose_landmarker_full.task')
OUT = os.path.join(ROOT, 'images/lineart/joints-real.json')

# MediaPipe/PoseLandmarker 索引
NOSE, EAR_L, EAR_R = 0, 7, 8
SH_L, SH_R, EL_L, EL_R, WR_L, WR_R = 11, 12, 13, 14, 15, 16
HIP_L, HIP_R, KN_L, KN_R, AN_L, AN_R = 23, 24, 25, 26, 27, 28
HEEL_L, HEEL_R, TOE_L, TOE_R = 29, 30, 31, 32


def load_cover_map():
    """pose_id -> 封面相对路径（取 manifest 里 final/pilot 的记录）"""
    man = json.load(open(os.path.join(ROOT, 'images/manifest.json')))
    out = {}
    for r in man['records']:
        if r.get('status') in ('final', 'pilot'):
            out.setdefault(r['pose_id'], r['file'])
    # 覆盖：app/public 里的成品封面优先（与线上展示一致）
    pub = os.path.join(ROOT, 'app/public/poses')
    if os.path.isdir(pub):
        for pid in list(out.keys()):
            p = os.path.join(pub, pid, 'cover.jpg')
            if os.path.exists(p):
                out[pid] = os.path.relpath(p, ROOT)
    return out


def to_norm(x_px, y_px, w, h):
    return [round(x_px / w, 5), round(y_px / h, 5)]


def main():
    pose_ids = [p['id'] for p in json.load(
        open(os.path.join(ROOT, 'app/src/data/poses.json')))['poses']]
    covers = load_cover_map()

    opts = vision.PoseLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=MODEL),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
    )
    landmarker = vision.PoseLandmarker.create_from_options(opts)

    result = {
        'meta': {
            'version': 2,
            'source': 'MediaPipe PoseLandmarker full (real detection on covers)',
            'canvas': {'w': 3, 'h': 4},
            'unit': 'normalized 0-1',
            'lrConvention': 'viewer-left / viewer-right（已从人物自身左右翻转）',
            'note': 'headTop/chin 由鼻尖与肩宽比例推导（MediaPipe 不含头顶与下巴点）',
        },
        'poses': {},
        'failed': {},
    }

    for pid in pose_ids:
        rel = covers.get(pid)
        if not rel:
            result['failed'][pid] = 'no cover'
            continue
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            result['failed'][pid] = 'cover missing'
            continue

        img = Image.open(path).convert('RGB')
        W, H = img.size
        mp_img = mpp.Image if False else None  # noqa: F841  (保持导入形态清晰)
        import mediapipe as mp
        mpimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(img))
        res = landmarker.detect(mpimg)
        if not res.pose_landmarks:
            result['failed'][pid] = 'no pose detected'
            continue

        l = res.pose_landmarks[0]
        px = lambda i: (l[i].x * W, l[i].y * H)  # noqa: E731
        vis = lambda i: float(getattr(l[i], 'visibility', 0.0))  # noqa: E731

        # 可见度体检：躯干四点必须可信，否则视为失败（交给前端空态）
        core = [SH_L, SH_R, HIP_L, HIP_R]
        if min(vis(i) for i in core) < 0.4:
            result['failed'][pid] = f'low core visibility (min={min(vis(i) for i in core):.2f})'
            continue

        # ---- 头高估算：用「肩点纵坐标 - 鼻尖纵坐标」×1.05 ----
        # 不用肩宽 ×0.62：水平尺寸受透视/转身影响大，会让远景人物头算得过小，
        # 进而把 8 头长误算成 9~10 头长。竖向量级更稳，且与 ST-01 手工实测吻合
        # （鼻 461px、肩 691px → 头高 242px，与网格实测完全一致）。
        nose_x, nose_y = px(NOSE)
        sh_mid_y = (px(SH_L)[1] + px(SH_R)[1]) / 2
        vert = sh_mid_y - nose_y
        sw_px = abs(px(SH_L)[0] - px(SH_R)[0])
        head_h = 1.05 * vert if vert > 0.02 * H else 0.62 * sw_px
        head_h = max(head_h, 0.05 * H)  # 下限防止远景小人物把比例算爆
        head_top = (nose_x, nose_y - 0.80 * head_h)
        chin = (nose_x, nose_y + 0.20 * head_h)

        # 画面左/右：MediaPipe 的 L 是人物自身左侧，正对镜头时出现在画面右
        # 用耳朵 x 判断朝向，若鼻在左耳右侧则视为正对/背对，需要翻转
        ear_lx, ear_rx = px(EAR_L)[0], px(EAR_R)[0]
        facing_camera = ear_lx > ear_rx  # 人物自身左耳在画面右侧 → 面向镜头
        if facing_camera:
            sh_l, sh_r = px(SH_R), px(SH_L)
            el_l, el_r = px(EL_R), px(EL_L)
            wr_l, wr_r = px(WR_R), px(WR_L)
            hip_l, hip_r = px(HIP_R), px(HIP_L)
            kn_l, kn_r = px(KN_R), px(KN_L)
            an_l, an_r = px(AN_R), px(AN_L)
        else:
            sh_l, sh_r = px(SH_L), px(SH_R)
            el_l, el_r = px(EL_L), px(EL_R)
            wr_l, wr_r = px(WR_L), px(WR_R)
            hip_l, hip_r = px(HIP_L), px(HIP_R)
            kn_l, kn_r = px(KN_L), px(KN_R)
            an_l, an_r = px(AN_L), px(AN_R)

        foot_y = max(px(TOE_L)[1], px(TOE_R)[1], px(HEEL_L)[1], px(HEEL_R)[1])
        body_axis_x = np.mean([sh_l[0], sh_r[0], hip_l[0], hip_r[0]])

        result['poses'][pid] = {
            'headTop': to_norm(*head_top, W, H),
            'headCenter': to_norm(ear_lx / 2 + ear_rx / 2, l[EAR_L].y * H, W, H),
            'nose': to_norm(nose_x, nose_y, W, H),
            'chin': to_norm(*chin, W, H),
            'shoulderL': to_norm(*sh_l, W, H),
            'shoulderR': to_norm(*sh_r, W, H),
            'elbowL': to_norm(*el_l, W, H),
            'elbowR': to_norm(*el_r, W, H),
            'wristL': to_norm(*wr_l, W, H),
            'wristR': to_norm(*wr_r, W, H),
            'hipL': to_norm(*hip_l, W, H),
            'hipR': to_norm(*hip_r, W, H),
            'kneeL': to_norm(*kn_l, W, H),
            'kneeR': to_norm(*kn_r, W, H),
            'ankleL': to_norm(*an_l, W, H),
            'ankleR': to_norm(*an_r, W, H),
            'bodyAxisX': round(float(body_axis_x / W), 5),
            'footBottomY': round(float(foot_y / H), 5),
            'visibility': {
                'core': round(min(vis(i) for i in core), 2),
                'limbs': round(min(vis(i) for i in (EL_L, EL_R, WR_L, WR_R, KN_L, KN_R)), 2),
            },
            'headHeight': round(float(head_h / H), 5),
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    ok, bad = len(result['poses']), len(result['failed'])
    print(f'joints-real.json: 成功 {ok} / 失败 {bad} / 共 {ok + bad}')
    if bad:
        for k, v in result['failed'].items():
            print(f'  失败 {k}: {v}')


if __name__ == '__main__':
    main()
