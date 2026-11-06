#!/usr/bin/env python3
"""
从真实关节坐标（joints-real.json）派生易错标注，写入 app/src/data/pose-annotations.json。

设计要点：
1. ST-01..ST-10 保留已人工逐张校准的版本（网格实测，视觉验收通过），不被覆盖。
2. 其余姿势从 MediaPipe 真实检测的关节坐标派生：下巴/肩线/肢体/头身比四处。
3. 头身比由 (脚底 - 头顶) / 头高 真实算出，不是套模板数字。
4. 半身/特写取景用「头顶到画幅下沿」而非脚底，避免不存在的脚被当成比例基准。
5. 检测失败的姿势不生成标注 —— 详情页只显示例图+线稿，不装假标注。

用法：python3 tools/build_annotations.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOINTS = os.path.join(ROOT, 'images/lineart/joints-real.json')
ANN = os.path.join(ROOT, 'app/src/data/pose-annotations.json')
POSES = os.path.join(ROOT, 'app/src/data/poses.json')

# 各体例的 4 条文案：(下巴, 肩线, 肢体, 比例)
COPY = {
    'SIT': ('下巴微收，别缩脖驼背',
            '双肩放松下沉，别耸到耳朵',
            '手臂自然搭在膝上，别夹紧腋下',
            '坐姿也要拉长上半身，别含胸'),
    'STREET': ('回头时下巴微收，别抬成仰视',
               '肩线顺着街面走，别歪肩',
               '手臂留出空隙，别贴着外套',
               '脚底踩稳地面，别切掉鞋尖'),
    'TRAVEL': ('下巴微收，别被帽子挡成抬头',
               '双肩放平，背包别压单边',
               '抬手时腋下打开，别夹住',
               '人物占画面约 2/3，别顶满'),
    'HOME': ('下巴微收，别低头挤出双下巴',
             '双肩放松，别前倾耸肩',
             '手臂自然放，别绷直撑桌面',
             '半身取景：头顶留白约 1/10'),
    'CAFE': ('下巴微收，视线略低于镜头',
             '双肩放平，别含胸缩颈',
             '端杯的手别挡脸，手臂留缝',
             '近景：头部约占画幅 1/3'),
    'BACK': ('略微回头即可，别整个扭过去',
             '双肩等高，别一高一低',
             '手臂别夹死，风里也要留缝',
             '地平线别切头，留呼吸空间'),
    'PROP': ('下巴微收，别被道具挡成抬头',
             '双肩下沉，别缩着躲道具',
             '握道具的手腕放松，别夹臂',
             '道具与人物比例要协调'),
    'SCENE': ('下巴微收，别顶出双下巴',
              '双肩等高，别被环境带歪',
              '手臂留空隙，别贴着身体',
              '脚步踩稳，重心别悬空'),
}

# 全身类（才用脚底做头身比基准）
FULL_BODY = {'ST', 'STREET', 'TRAVEL', 'BACK', 'SCENE'}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def r4(v):
    return round(float(v), 4)


def build(pid, p, cat):
    head_h = p['headHeight']
    chin = p['chin']
    hc = p['headCenter']
    shl, shr = p['shoulderL'], p['shoulderR']
    wl, wr = p['wristL'], p['wristR']
    hip = ((p['hipL'][0] + p['hipR'][0]) / 2, (p['hipL'][1] + p['hipR'][1]) / 2)
    # 归一化坐标里 x 单位 = W、y 单位 = H，H = 4/3 W → 头宽换算成 x 单位
    head_w = clamp(head_h * 0.96, 0.03, 0.45)
    head_top_y = p['headTop'][1]
    foot_y = p['footBottomY']
    sh_y = (shl[1] + shr[1]) / 2

    c_chin, c_sh, c_limb, c_ratio = COPY[cat]
    marks = []

    # ---- ① 下巴带：横向框住脸下半部 ----
    marks.append({
        'id': 'chin',
        'type': 'rect',
        'tone': 'danger',
        'x': r4(hc[0] - head_w / 2),
        'y': r4(chin[1] - head_h * 0.38),
        'w': r4(head_w),
        'h': r4(head_h * 0.46),
        'rx': 0.012,
        'label': c_chin,
        'labelAt': [r4(clamp(hc[0] - head_w - 0.12, 0.06, 0.8)),
                    r4(clamp(chin[1] - head_h * 0.15, 0.06, 0.9))],
    })

    # ---- ② 肩线：连接两肩的等高参考 ----
    x1 = min(shl[0], shr[0]) - 0.035
    x2 = max(shl[0], shr[0]) + 0.035
    marks.append({
        'id': 'shoulders',
        'type': 'hline',
        'tone': 'guide',
        'y': r4(sh_y),
        'x1': r4(clamp(x1, 0, 1)),
        'x2': r4(clamp(x2, 0, 1)),
        'label': c_sh,
        'labelAt': [r4(clamp(x2 + 0.02, 0.1, 0.85)), r4(clamp(sh_y, 0.05, 0.92))],
    })

    # ---- ③ 肢体：抬手类用箭头，垂手类用矩形 ----
    arms_up = min(wl[1], wr[1]) < sh_y - 0.02
    if arms_up:
        up_l = wl[1] <= wr[1]
        src, dst = (shl, wl) if up_l else (shr, wr)
        marks.append({
            'id': 'limb',
            'type': 'arrow',
            'tone': 'guide',
            'from': [r4(src[0]), r4(src[1])],
            'to': [r4(dst[0]), r4(dst[1])],
            'label': c_limb,
            'labelAt': [r4(clamp(dst[0] + 0.06 if dst[0] < 0.5 else dst[0] - 0.2, 0.05, 0.8)),
                        r4(clamp(dst[1] + 0.06, 0.05, 0.92))],
        })
    else:
        xs = [shl[0], shr[0], wl[0], wr[0]]
        ys = [sh_y, wl[1], wr[1]]
        bx1, bx2 = min(xs) - 0.025, max(xs) + 0.025
        by1 = min(ys) - 0.02
        by2 = max(ys) + 0.03
        marks.append({
            'id': 'limb',
            'type': 'rect',
            'tone': 'guide',
            'x': r4(clamp(bx1, 0, 1)),
            'y': r4(clamp(by1, 0, 1)),
            'w': r4(clamp(bx2 - bx1, 0.05, 1)),
            'h': r4(clamp(by2 - by1, 0.05, 1)),
            'rx': 0.018,
            'label': c_limb,
            'labelAt': [r4(clamp(bx1 - 0.14, 0.05, 0.8)), r4(clamp((by1 + by2) / 2, 0.06, 0.9))],
        })

    # ---- ④ 比例：只在头身比可信时报具体数字 ----
    # 头高由「肩点 - 鼻尖」竖向量级推导，抬头/低头/转身会带来偏差，
    # 实测分布 -1.8~12.7（中位 8.0）。教学数字不能瞎报：
    # 落进 6.5–9.0 才给「约 N 个头长」，否则用不含数字的通用文案。
    span = foot_y - head_top_y
    ratio = span / max(head_h, 1e-6)
    looks_full = cat in FULL_BODY and foot_y < 0.975 and span > 0
    trusted = looks_full and 6.5 <= ratio <= 9.0
    if trusted:
        div = int(clamp(round(ratio), 6, 9))
        ratio_label = f'约 {div} 个头长：{c_ratio}'
        y0, y1 = head_top_y, foot_y
    elif looks_full and 4.0 <= ratio <= 12.0:
        # 构图确实全身，但头高估不准 → 画刻度但不报数字
        div = 7
        ratio_label = c_ratio
        y0, y1 = head_top_y, foot_y
    else:
        # 半身/特写取景：量到画幅下沿或髋下，不以不存在的脚为基准
        div = 5
        bottom = clamp(max(foot_y if 0 < foot_y < 1 else 0, hip[1] + 0.32), 0.5, 0.995)
        ratio_label = c_ratio
        y0, y1 = head_top_y, bottom
    marks.append({
        'id': 'ratio',
        'type': 'ruler',
        'tone': 'measure',
        'axis': 'y',
        'from': r4(clamp(y0, 0.01, 0.99)),
        'to': r4(clamp(y1, 0.02, 1)),
        'divisions': div,
        'label': ratio_label,
        'labelAt': [0.16, r4(clamp((y0 + y1) / 2, 0.1, 0.9))],
    })

    return {
        'canvas': {'w': 3, 'h': 4},
        'caption': None,   # 由类目句式 + 姿势名合成，见下
        'guides': {'axisX': r4(p['bodyAxisX'])},
        'marks': marks,
    }


def main():
    joints = json.load(open(JOINTS))
    poses = {p['id']: p for p in json.load(open(POSES))['poses']}
    old = json.load(open(ANN))
    out = {}

    for pid, p in joints['poses'].items():
        if pid.startswith('ST-'):
            continue  # ST 类保留人工校准版
        pose = poses.get(pid)
        if not pose:
            continue
        cat = pose['category']
        if cat not in COPY:
            continue
        entry = build(pid, p, cat)
        entry['caption'] = f"{pose['name']}：按①②③④依次调整"
        out[pid] = entry

    # 合并：人工版 ST 优先，其余用派生版
    merged = {}
    for pid, v in old['poses'].items():
        if pid.startswith('ST-'):
            merged[pid] = v
    merged.update(out)

    data = {
        'meta': {
            'version': 3,
            'generated': '2026-11-05',
            'note': ('ST-01..ST-10 为 10×10 网格叠加人工校准；其余由 '
                     'tools/build_annotations.py 从 MediaPipe 真实关节坐标派生。'
                     'x/y 归一化 0–1，画幅 3:4；换封面后需重跑 tools/extract_joints.py。'),
            'source': 'images/lineart/joints-real.json',
        },
        'poses': dict(sorted(merged.items())),
    }
    with open(ANN, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    n_manual = sum(1 for k in merged if k.startswith('ST-'))
    print(f'pose-annotations.json: {len(merged)} 条（人工 {n_manual} + 派生 {len(merged) - n_manual}）')
    missing = [k for k in poses if k not in merged]
    print(f'无标注 {len(missing)} 条（详情页只显示例图/线稿）：{missing}')


if __name__ == '__main__':
    main()
