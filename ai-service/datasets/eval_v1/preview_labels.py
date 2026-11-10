"""Draws labels on the eval images (boxes, skeleton; figure's left = cyan, right = orange) for a visual check.
usage: python preview_labels.py <out.jpg> [--keypoints-only]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BONES = [("head", "neck"), ("neck", "chest"), ("chest", "waist"), ("neck", "left_shoulder"), ("neck", "right_shoulder"),
         ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"), ("right_shoulder", "right_elbow"),
         ("right_elbow", "right_wrist"), ("waist", "left_hip"), ("waist", "right_hip"), ("left_hip", "left_knee"),
         ("left_knee", "left_ankle"), ("right_hip", "right_knee"), ("right_knee", "right_ankle")]


def color(name: str) -> str:
    return "cyan" if name.startswith("left") else "orange" if name.startswith("right") else "yellow"


def main() -> None:
    here = Path(__file__).parent
    doc = json.loads((here / "annotations.json").read_text(encoding="utf-8"))
    only_kp = "--keypoints-only" in sys.argv
    tiles = []
    for img in doc["images"]:
        figs = img["figures"]
        if only_kp and not any("keypoints" in f for f in figs):
            continue
        im = Image.open(here / "images" / img["file"]).convert("RGB")
        im.thumbnail((360, 360))
        w, h = im.size
        d = ImageDraw.Draw(im)
        for f in figs:
            x0, y0, x1, y1 = f["bbox"]
            d.rectangle([x0 * w, y0 * h, x1 * w, y1 * h], outline="grey" if f.get("ignore") else "lime", width=2)
            k = f.get("keypoints", {})
            for a, b in BONES:
                if k.get(a, [0, 0, 0])[2] and k.get(b, [0, 0, 0])[2]:
                    d.line([k[a][0] * w, k[a][1] * h, k[b][0] * w, k[b][1] * h], fill=color(b if b != "neck" else a), width=3)
            for n, (x, y, v) in k.items():
                if v:
                    r = 4
                    d.ellipse([x * w - r, y * h - r, x * w + r, y * h + r], fill=color(n) if v == 2 else None, outline="black")
        d.text((4, 4), img["file"], fill="white")
        tiles.append(im)
    cols, cell = 6, 370
    sheet = Image.new("RGB", (cols * cell, ((len(tiles) + cols - 1) // cols) * cell), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * cell + 5, (i // cols) * cell + 5))
    sheet.save(sys.argv[1], quality=85)
    print(len(tiles), "tiles")


if __name__ == "__main__":
    main()
