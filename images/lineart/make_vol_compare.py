#!/usr/bin/env python3
"""合成体积人偶复测对照图 _vol-compare.png

每行一条姿势，5 列：封面实拍 / 细线骨架控制图 / 人偶控制图 / 上轮细线出图 / 本轮人偶出图
判定写在行尾列头下方，便于一眼看出"手臂是否保住 + 是否与封面同姿势"。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
COVERS = HERE.parent

TILE_W, TILE_H = 300, 400
PAD, TOP, LEFT = 14, 76, 150          # LEFT = 留给行标签
HEAD_H = 92

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
INK = (0x2E, 0x29, 0x25)
BG = (0xFA, 0xF7, 0xF0)
GREY = (0x8A, 0x84, 0x7B)
PASS = (0x2F, 0x6B, 0x3E)
FAIL = (0xA8, 0x3A, 0x2E)

ROWS = [
    ("ST-04", "双手插袋",
     "images/ST-04.jpg", "skeleton/_ai-input/_skeleton-ai-ST-04.png", "_vol-ai-ST-04.png",
     "ST-04.png", "_vol-ST-04.png",
     "× 未保住：两手被模型收到身前扣在一起（控制图里两手分居胯侧袋位、相距约两掌），读作「双手交握」，插袋语义丢失；与上轮同类失败"),
    ("ST-05", "松弛环抱",
     "images/ST-05.jpg", "skeleton/_ai-input/_skeleton-ai-ST-05.png", "_vol-ai-ST-05.png",
     "ST-05.png", "_vol-ST-05.png",
     "√ 保住：两条前臂水平叠抱、手插进对侧臂弯，与封面同姿势（上轮被抹平成自然下垂）"),
    ("ST-09", "踮脚伸展",
     "images/ST-09.jpg", "skeleton/_ai-input/_skeleton-ai-ST-09.png", "_vol-ai-ST-09.png",
     "ST-09.png", "_vol-ST-09.png",
     "√ 保住：侧视双臂过头相扣、后仰、踮脚，与封面同姿势（上轮双臂被放下）"),
]

COLS = ["封面实拍（判定基准）", "① 细线骨架控制图（上轮）", "② 人偶控制图（本轮）",
        "上轮出图（骨架）", "本轮出图（人偶）"]


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def wrap(d, text, xy, maxw, f, lh, fill):
    """按宽度逐字折行（中文按字符切，够用）。返回下一行 y。"""
    x, y = xy
    line = ""
    for ch in text:
        if d.textlength(line + ch, font=f) > maxw and line:
            d.text((x, y), line, font=f, fill=fill)
            y += lh
            line = ch
        else:
            line += ch
    if line:
        d.text((x, y), line, font=f, fill=fill)
        y += lh
    return y


def fit(path, w, h):
    im = Image.open(path).convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), (0xFF, 0xFF, 0xFF))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def main():
    ncol = len(COLS)
    W = LEFT + PAD + ncol * (TILE_W + PAD)
    rowh = TILE_H + 46 + PAD
    H = TOP + HEAD_H + len(ROWS) * rowh + 190
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, TOP + HEAD_H - 10], fill=(0xEE, 0xE9, 0xDE))
    d.text((LEFT, 22), "线稿控制图升级复测：细线骨架 vs 有体积人偶（ST-04 / ST-05 / ST-09）",
           font=font(34), fill=INK)
    d.text((LEFT, 72), "同一套关节坐标、同一提示词、同 seed 策略 —— 唯一变量 = 控制图是否携带体量",
           font=font(21), fill=GREY)

    for c, name in enumerate(COLS):
        x = LEFT + PAD + c * (TILE_W + PAD)
        d.text((x, TOP + 26), name, font=font(20), fill=INK)

    for r, (pid, pname, cover, sk, vol_ctrl, old, new, verdict) in enumerate(ROWS):
        y = TOP + HEAD_H + r * rowh
        d.text((18, y + 150), pid, font=font(30), fill=INK)
        d.text((18, y + 192), pname, font=font(24), fill=GREY)
        paths = [COVERS.parent / cover, HERE / sk, HERE / vol_ctrl, HERE / old, HERE / new]
        for c, p in enumerate(paths):
            x = LEFT + PAD + c * (TILE_W + PAD)
            if Path(p).exists():
                img.paste(fit(p, TILE_W, TILE_H), (x, y))
            d.rectangle([x, y, x + TILE_W - 1, y + TILE_H - 1], outline=(0xD5, 0xCE, 0xC0))
        ok = verdict.startswith("√")
        wrap(d, verdict, (LEFT + PAD, y + TILE_H + 12), TILE_W * 5 + PAD * 4, font(21),
             24, PASS if ok else FAIL)

    y = TOP + HEAD_H + len(ROWS) * rowh + 6
    d.line([(LEFT, y), (W - PAD, y)], fill=(0xD5, 0xCE, 0xC0), width=2)
    lines = [
        "结论 B（部分有效）：跨躯干（ST-05）与侧视上举（ST-09）由「失败」翻为「通过」；"
        "手臂贴近躯干且需与衣物/身体产生遮挡关系的 ST-04 仍失败。",
        "判据：① 手臂动作是否保住（肘/腕朝向、与躯干相对关系）② 对照封面能否认出是同一姿势。"
        "本轮 3 张 × 0.12 = 0.36 元，与预算一致；文字补强分支未跑（预算已用尽）。",
    ]
    yy = y + 18
    for t in lines:
        yy = wrap(d, t, (LEFT, yy), W - LEFT - PAD - 10, font(21), 30, INK) + 10

    out = HERE / "_vol-compare.png"
    img.save(out, "PNG", optimize=True)
    print(f"{out} {img.size} {out.stat().st_size / 1024:.0f}KB")


if __name__ == "__main__":
    main()
