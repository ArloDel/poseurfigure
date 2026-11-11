"""Builds the pose catalog from catalog/manifest.json.

usage (from ai-service/):  python -m catalog.build [--preview <dir>]

For every pose: fetch the reference photo (or read it from design/img), crop if the manifest says so,
save it to backend/public/catalog/<slug>.jpg, run the same detector and pose model as user photos,
and write keypoints, angles, instructions and limit warnings to shared/catalog/poses.json.
Using the same models for the catalog and for user photos keeps both sides directly comparable.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

from app.config import get_settings
from app.schemas.analysis import FigureDetection
from app.services.pose_extractor import build_pose
from app.services.profiles import load_profiles
from catalog.instructions import build_instructions, constraints

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("manifest.json")
PHOTOS = ROOT / "backend" / "public" / "catalog"
OUT = ROOT / "shared" / "catalog" / "poses.json"
MAX_SIDE = 900
# A pose is only useful for matching if its body is readable: enough joints, and the torso anchors
# that positions are measured from. Poses that fail stay in the file but are not published.
MIN_VISIBLE = 10
ANCHORS = ("neck", "left_hip", "right_hip")


def review(pose) -> str | None:
    """Why a pose can't be published, or None if it can."""
    missing = [a for a in ANCHORS if pose.keypoints[a].visibility != "visible"]
    if missing:
        return f"torso anchors not visible: {', '.join(missing)}"
    if pose.visible_count < MIN_VISIBLE:
        return f"only {pose.visible_count} joints visible (need {MIN_VISIBLE})"
    return None


def load_photo(src: dict) -> Image.Image:
    if "file" in src:
        im = Image.open(ROOT / src["file"])
    else:
        req = urllib.request.Request(src["url"], headers={"User-Agent": "figurepose-catalog/0.1"})
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read()))
    im = im.convert("RGB")
    if "crop" in src:
        x0, y0, x1, y1 = src["crop"]
        im = im.crop((round(x0 * im.width), round(y0 * im.height), round(x1 * im.width), round(y1 * im.height)))
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    return im


def preview(im: Image.Image, pose, path: Path) -> None:
    im = im.copy()
    d = ImageDraw.Draw(im)
    w, h = im.size
    color = lambda n: "cyan" if n.startswith("left") else "orange" if n.startswith("right") else "yellow"  # noqa: E731
    k = pose.keypoints
    for a, b in [("head", "neck"), ("neck", "chest"), ("chest", "waist"), ("neck", "left_shoulder"), ("neck", "right_shoulder"),
                 ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"), ("right_shoulder", "right_elbow"),
                 ("right_elbow", "right_wrist"), ("waist", "left_hip"), ("waist", "right_hip"), ("left_hip", "left_knee"),
                 ("left_knee", "left_ankle"), ("right_hip", "right_knee"), ("right_knee", "right_ankle")]:
        if k[a].x is not None and k[b].x is not None:
            d.line([k[a].x * w, k[a].y * h, k[b].x * w, k[b].y * h], fill=color(b if b != "neck" else a), width=4)
    im.save(path, quality=85)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", help="folder for skeleton previews to review")
    args = ap.parse_args()

    from app.main import build_pipeline

    settings = get_settings()
    profiles = load_profiles(settings.skeleton_profiles_path)
    pipe = build_pipeline()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    PHOTOS.mkdir(parents=True, exist_ok=True)
    if args.preview:
        Path(args.preview).mkdir(parents=True, exist_ok=True)

    poses = []
    for entry in manifest["poses"]:
        src, profile = entry["image"], profiles[entry["profile"]]
        im = load_photo(src)
        im.save(PHOTOS / f"{entry['slug']}.jpg", quality=85, optimize=True)

        dets = pipe.detector.detect(im)
        if not dets:
            print(f"!! {entry['slug']}: no figure detected, skipped")
            continue

        figs = [FigureDetection(bbox=list(d.bbox), score=d.score) for d in dets]
        box = tuple(figs[pipe.pick(figs)].bbox)
        pose = build_pose(pipe.estimator.estimate(im, box), profile, im.size)
        aspect = im.width / im.height

        problem = review(pose)
        poses.append({
            "slug": entry["slug"], "name": entry["name"], "profile": entry["profile"],
            "published": problem is None,
            "review_note": problem,
            "category": entry["category"], "difficulty": entry["difficulty"], "description": entry["description"],
            "image": {"path": f"catalog/{entry['slug']}.jpg", "width": im.width, "height": im.height},
            "credit": {k: src[k] for k in ("title", "creator", "license", "source")} | ({"modified": "cropped and resized"} if "crop" in src else {"modified": "resized"}),
            "figure_box": [round(v, 4) for v in box],
            "keypoints": {n: {"x": k.x, "y": k.y, "visibility": k.visibility} for n, k in pose.keypoints.items()},
            "joint_angles": pose.joint_angles,
            "orientation": pose.orientation,
            "instructions": build_instructions(pose.joint_angles, pose.keypoints, aspect),
            "constraints": constraints(pose.joint_angles, profile.joints),
            "models": pipe.models,
        })
        if args.preview:
            preview(im, pose, Path(args.preview) / f"{entry['slug']}.jpg")
        print(f"{'ok' if problem is None else '--'} {entry['slug']:20} {pose.visible_count:2} visible{'' if problem is None else ': ' + problem}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "generated_by": "ai-service/catalog/build.py", "poses": poses}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    published = [p for p in poses if p["published"]]
    by_profile = {pr: sum(1 for p in published if p["profile"] == pr) for pr in sorted({p["profile"] for p in poses})}
    print(f"{len(poses)} poses ({len(published)} published: {by_profile}) -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
