#!/usr/bin/env python3
"""出图自查拼版：封面 | AI 线稿，每张 20 条，便于逐条对照是否同姿势。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
CW, CH = 200, 267
COLS, ROWS = 5, 4


def main():
    ids = sys.argv[1:] or [p.stem for p in sorted(HERE.glob("*.png"))
                           if len(p.stem.split("-")) == 2 and p.stem[:2].isalpha()
                           and not p.stem.startswith("_")]
    per = COLS * ROWS
    for si in range(0, len(ids), per):
        chunk = ids[si:si + per]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (CW * 2 * COLS, (CH + 16) * rows), (252, 250, 246))
        d = ImageDraw.Draw(sheet)
        for i, pid in enumerate(chunk):
            x = (i % COLS) * CW * 2
            y = (i // COLS) * (CH + 16)
            cov = HERE.parent / f"{pid}.jpg"
            out = HERE / f"{pid}.png"
            if cov.exists():
                sheet.paste(Image.open(cov).convert("RGB").resize((CW, CH)), (x, y + 16))
            if out.exists():
                sheet.paste(Image.open(out).convert("RGB").resize((CW, CH)), (x + CW, y + 16))
            d.text((x + 4, y + 3), f"{pid}  cover | AI", fill=(60, 40, 20))
        p = HERE / f"_review-{si // per + 1}.png"
        sheet.save(p, "PNG", optimize=True)
        print(p, len(chunk))


if __name__ == "__main__":
    main()
