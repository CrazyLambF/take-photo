#!/usr/bin/env python3
"""把 final/ 下的原始出图收口成交付件 images/lineart/{ID}.png

交付约束：1080x1440（封面 3:4）、<=20KB、双色（深炭灰墨线 + 奶油底）。
ST-01 这一张来自 trial 批（路线 A 首跑即达标，省一张的钱），其余来自 final 批。

用法：python3 finalize.py [--dilate 1]
"""
import argparse
import json
from pathlib import Path

import postprocess as P

HERE = Path(__file__).resolve().parent

# ST-01 是试跑那张；其余在 final 批
SOURCES = {f"ST-{i:02d}": HERE / "trial" / "raw-ST-01-A.jpg" for i in (1,)}
for i in range(2, 11):
    SOURCES[f"ST-{i:02d}"] = HERE / "final" / f"raw-ST-{i:02d}-A.jpg"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dilate", type=int, default=1)
    args = ap.parse_args()

    rows, missing = [], []
    for pid, src in SOURCES.items():
        if not src.exists():
            missing.append(f"{pid} ({src.name})")
            continue
        dst = HERE / f"{pid}.png"
        size, cov = P.process(src, dst, dil=args.dilate)
        rows.append(dict(id=pid, file=dst.name, bytes=size, kb=round(size / 1024, 1),
                         within_20kb=size <= P.LIMIT, ink_ratio=round(cov, 4),
                         w=P.W, h=P.H, source=str(src.relative_to(HERE))))
        flag = "OK " if size <= P.LIMIT else "OVER"
        print(f"{pid}  {size / 1024:5.1f}KB  {flag}  ink={cov:.3f}")

    (HERE / "_final-index.json").write_text(
        json.dumps(dict(count=len(rows), limit_bytes=P.LIMIT, items=rows),
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = sum(r["within_20kb"] for r in rows)
    total = sum(r["bytes"] for r in rows)
    print(f"\n{len(rows)} 张已收口；<=20KB {ok}/{len(rows)}；合计 {total / 1024:.1f}KB"
          f"（均 {(total / max(1, len(rows))) / 1024:.1f}KB）")
    if missing:
        print("缺原始出图：" + ", ".join(missing))


if __name__ == "__main__":
    main()
