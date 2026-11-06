#!/usr/bin/env python3
"""从《拍照姿势App项目计划.md》§2.1/§2.2 + images/prompts/pose-prompts-100.json 生成
app/src/data/poses.json 与 category-tips.json，并复制封面图到 app/public/poses/。
构建期校验：100 条、ID 唯一、10 类 × 10、必填字段。
"""
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = (ROOT / '拍照姿势App项目计划.md').read_text(encoding='utf-8')
PROMPTS = json.loads((ROOT / 'images/prompts/pose-prompts-100.json').read_text(encoding='utf-8'))
MANIFEST = json.loads((ROOT / 'images/manifest.json').read_text(encoding='utf-8'))

CAT_NAMES = {}
for m in re.finditer(r'^\| [A-J] \| (.+?) \| ([A-Z]+) \| 10 \| (.+?) \| (.+?) \|$', PLAN, re.M):
    CAT_NAMES[m.group(2)] = {'name': m.group(1), 'coverage': m.group(3), 'machine': m.group(4)}
assert len(CAT_NAMES) == 10, f'§2.1 类目解析异常: {len(CAT_NAMES)}'

poses, tips_src, cur_code, cur_tip = [], {}, None, None
row_re = re.compile(r'^\| ([A-Z]+-\d{2}) \| (.+?) \| (.+?) \| (.+?) \| (\d) \|$', re.M)
lines = PLAN.splitlines()
# 逐行扫描以关联「通用要点」与当前类目
pending_rows = []
for i, ln in enumerate(lines):
    h = re.match(r'^#### [A-J]\. .+?（([A-Z]+)[，）]', ln)
    if h:
        cur_code = h.group(1)
        continue
    if ln.startswith('通用要点') and cur_code:
        tips_src[cur_code] = ln.split('：', 1)[1].strip()
    for m in row_re.finditer(ln):
        pending_rows.append((cur_code, m))

def extract_light(s):
    out = []
    for kw, val in [('黄金时刻', '黄金时刻'), ('黄昏', '黄金时刻'), ('夜', '夜景'), ('逆光', '逆光'),
                    ('人造', '人造光'), ('灯', '人造光'), ('自然光', '自然光'), ('天光', '自然光'),
                    ('阴天', '自然光'), ('柔', '自然光')]:
        if kw in s and val not in out:
            out.append(val)
    return out or ['自然光']

def extract_focal(s):
    m = re.search(r'等效[^，。;；]*mm[^，。;；]*|手机\s*\d[xX～~\-–\d]*倍?', s)
    return m.group(0).strip() if m else ''

def extract_angle(s):
    for kw in ['平视', '低机位', '俯拍', '仰拍', '腰平', '高机位']:
        if kw in s:
            return kw
    return ''

def extract_settings(s):
    ms = re.findall(r'[Ff]/\d(?:\.\d)?|\d\.\d[-–]?\d* 光圈|快门[^，。;；]*|人像模式|连拍 ?\d*[-–]?\d* ?张?', s)
    return '，'.join(dict.fromkeys(ms))[:60]

TAG_KWS = ['回眸','背影','坐','站','躺','走','窗','花','伞','夜','雨','雪','海','书','咖啡','机场','地铁','野餐','街拍','旅行','居家','特写','逆光','光斑','全身','半身']
PROP_KWS = {'花':'花束','气球':'气球','书':'书本','咖啡':'咖啡','伞':'伞','行李箱':'行李箱','野餐篮':'野餐篮','耳机':'耳机','泡泡':'泡泡机','猫':'宠物','单车':'自行车','甜筒':'甜筒','琴':'乐器','画':'画册'}
MISTAKES = {
 'ST': ['重心不稳，身体歪斜', '双臂贴死身体显壮', '下巴上扬显鼻孔'],
 'SIT': ['坐满整张椅子显得松垮', '膝盖正对镜头挤压腿部线条', '驼背含胸'],
 'STREET': ['刻意僵住等镜头，失去行进感（用连拍抓走动帧）', '头发遮脸或表情紧绷'],
 'TRAVEL': ['人物太大挡住地标（人小景大更耐看）', '逆光时脸部死黑没有补光'],
 'HOME': ['全靠顶灯照明，脸上有生硬阴影（改用窗光侧光）', '背景杂物太多抢走焦点'],
 'CAFE': ['手臂压在桌沿显肩宽', '道具举太高挡住脸'],
 'BACK': ['肩膀耸起不放松', '头顶切边、地平线压头'],
 'CLOSE': ['手部姿态没检查，出现畸形', '对焦落在背景，眼睛虚了'],
 'PROP': ['道具喧宾夺主，眼神不看镜头', '握持姿势僵硬，道具变成负担'],
 'SCENE': ['只顾场景忘了姿势基础（重心/线条）', '夜景或逆光没补光，脸部欠曝'],
}
STEPS_TMPL = ['进入场景，先确认光线方向与干净背景', '按要点摆位：{body}', '按机位取景（{framing}），连拍 3–5 张微调选优']

for code, m in pending_rows:
    pid, name, body, camera_text, diff = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))
    pp = next((x for x in PROMPTS['poses'] if x['id'] == pid), None)
    light_s = pp['light'] if pp else camera_text
    framing = pp['camera'] if (pp and pp.get('camera')) else camera_text
    focal = extract_focal(camera_text + ' ' + (pp['camera'] if pp else ''))
    tags = [CAT_NAMES[code]['name'].split(' ·')[0]]
    blob = name + body + framing + camera_text
    tags += [t for t in TAG_KWS if t in blob and t not in tags][:5]
    props = sorted({v for k, v in PROP_KWS.items() if k in blob})
    pose = {
        'id': pid, 'name': name, 'category': code, 'difficulty': diff, 'people': 1,
        'gear': ['phone', 'camera'],
        'light': extract_light(light_s),
        'camera': {'focal': focal, 'angle': extract_angle(camera_text), 'framing': framing,
                   'settings': extract_settings(camera_text)},
        'pose': {'body': body, 'hands': '', 'head': '', 'expression': ''},
        'steps': [s.format(body=body, framing=re.split(r'[，,]', framing)[0]) for s in STEPS_TMPL],
        'mistakes': MISTAKES[code],
        'images': {}, 'tags': tags[:6],
    }
    if props:
        pose['props'] = props
    poses.append(pose)

ids = [p['id'] for p in poses]
assert len(poses) == 100 and len(set(ids)) == 100, f'姿势数异常: {len(poses)} 唯一 {len(set(ids))}'
from collections import Counter
cnt = Counter(p['category'] for p in poses)
assert set(cnt.values()) == {10}, f'类目分布异常: {cnt}'
for p in poses:
    rec = next((r for r in MANIFEST['records'] if r['pose_id'] == p['id'] and r.get('status') in ('final', 'pilot')), None)
    if rec and (ROOT / rec['file']).exists():
        dst = ROOT / 'app/public/poses' / p['id'] / 'cover.jpg'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rec['file'], dst)
        p['images']['cover'] = f'poses/{p["id"]}/cover.jpg'
    # 线稿示意：images/lineart/{id}.png 存在则登记（构建期产物，缺失不填 → 前端走诚实空态）
    lineart_src = ROOT / 'images/lineart' / f'{p["id"]}.png'
    if lineart_src.exists() and lineart_src.stat().st_size > 0:
        dst = ROOT / 'app/public/poses' / p['id'] / 'lineart.png'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lineart_src, dst)
        p['images']['lineArt'] = f'poses/{p["id"]}/lineart.png'

tips = [{'category': c, 'name': CAT_NAMES[c]['name'],
         'tips': [{'type': 'composition', 'text': CAT_NAMES[c]['machine']},
                  {'type': 'light', 'text': tips_src.get(c, CAT_NAMES[c]['coverage'])}]}
        for c in CAT_NAMES]

out = {'meta': {'generated': '2026-11-02', 'copyStatus': 'derived-v1',
        'source': '计划 §2.2 详表 + pose-prompts-100.json v1.1 + manifest；文案打磨见决策 #15'},
       'poses': poses}
(ROOT / 'app/src/data/poses.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
(ROOT / 'app/src/data/category-tips.json').write_text(json.dumps({'meta': {'generated': '2026-11-02'}, 'categories': tips}, ensure_ascii=False, indent=1), encoding='utf-8')
cover_n = sum(1 for p in poses if p['images'].get('cover'))
print(f'poses.json: {len(poses)} 条（{dict(cnt)}），封面 {cover_n}/100')
print('tags 样例 ST-01:', poses[0]['tags'], '| light SCENE-01:', [p for p in poses if p['id']=='SCENE-01'][0]['light'])
print('category-tips: 10 类齐全' if len(tips) == 10 else 'tips 异常')
