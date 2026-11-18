"""Draws a target pose as a stick figure, to show an image model the pose instead of describing it in words.

Lines follow the skeleton profile's connections. The figure's left side is drawn in one color and its right
side in another, the same way on every image, so a provider can be told which is which. The drawing keeps
the target photo's aspect and framing: what is on the left of the drawing is on the left of the picture.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from app.schemas.analysis import SkeletonProfile
from app.services.pose_matcher import PoseView

LEFT = (40, 110, 255)    # figure's left side: blue
RIGHT = (255, 120, 20)   # figure's right side: orange
CENTER = (30, 30, 30)    # head, spine, hips


def _color(a: str, b: str) -> tuple[int, int, int]:
    if a.startswith("left_") and b.startswith("left_") or a.startswith("left_") and b in ("neck", "waist") \
            or b.startswith("left_") and a in ("neck", "waist"):
        return LEFT
    if a.startswith("right_") and b.startswith("right_") or a.startswith("right_") and b in ("neck", "waist") \
            or b.startswith("right_") and a in ("neck", "waist"):
        return RIGHT
    return CENTER


def draw_skeleton(target: PoseView, profile: SkeletonProfile, height: int = 1024) -> Image.Image:
    """White canvas with the target pose. Joints the target doesn't show are left out, with their lines."""
    width = max(1, round(height * target.aspect))
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    pts = {n: (k.x * width, k.y * height) for n, k in target.keypoints.items()
           if k.x is not None and k.y is not None and k.visibility == "visible"}
    line = max(4, height // 90)
    for a, b in profile.connections:
        if a in pts and b in pts:
            d.line([pts[a], pts[b]], fill=_color(a, b), width=line)
    r = line * 1.2
    for n, (x, y) in pts.items():
        fill = LEFT if n.startswith("left_") else RIGHT if n.startswith("right_") else CENTER
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    if "head" in pts:
        x, y = pts["head"]
        hr = line * 4
        d.ellipse([x - hr, y - hr, x + hr, y + hr], outline=CENTER, width=line)
    return img
