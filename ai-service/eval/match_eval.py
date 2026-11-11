"""Measure pose matching (Sprint 5) and write reports/match_v1.md.

usage (from ai-service/):  python -m eval.match_eval

1. Re-finding: every published catalog photo is altered (shifted and shrunk, or mirrored), run through the
   real detector and pose model, and matched against its profile's catalog. The original should rank first;
   a mirrored photo should be found and flagged as mirrored.
2. Stability: on eval_v1 figures with hand-labeled keypoints, the catalog ranking from labeled keypoints is
   compared with the ranking from predicted keypoints. Keypoint errors should not reshuffle recommendations.
3. Feasibility: how many catalog poses go past a profile's estimated joint limits.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

from app.config import get_settings
from app.schemas.analysis import FigureDetection, Keypoint
from app.services.pose_extractor import build_pose
from app.services.pose_matcher import PoseView, feasibility, match
from app.services.profiles import load_profiles

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "shared" / "catalog" / "poses.json"
PHOTOS = ROOT / "backend" / "public"


def view_from_catalog(p: dict) -> PoseView:
    kps = {n: Keypoint(x=k["x"], y=k["y"], confidence=1.0, visibility=k["visibility"]) for n, k in p["keypoints"].items()}
    return PoseView(kps, p["image"]["width"] / p["image"]["height"])


def shift_and_shrink(im: Image.Image) -> Image.Image:
    """The figure smaller and off-centre on a wider canvas: same pose, different framing."""
    w, h = im.size
    canvas = Image.new("RGB", (int(w * 1.5), int(h * 1.3)), tuple(int(c) for c in im.resize((1, 1)).getpixel((0, 0))))
    small = im.resize((int(w * 0.85), int(h * 0.85)))
    canvas.paste(small, (int(w * 0.6), int(h * 0.3)))
    return canvas


def rank(query: PoseView, catalog: list[dict], profile) -> list[tuple[str, float, bool]]:
    out = []
    for p in catalog:
        m = match(query, view_from_catalog(p), profile)
        out.append((p["slug"], m.similarity, m.mirrored))
    return sorted(out, key=lambda r: r[1], reverse=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from app.main import build_pipeline

    settings = get_settings()
    profiles = load_profiles(settings.skeleton_profiles_path)
    pipe = build_pipeline()
    catalog = [p for p in json.loads(CATALOG.read_text(encoding="utf-8"))["poses"] if p["published"]]
    by_profile = {pr: [p for p in catalog if p["profile"] == pr] for pr in profiles}

    # --- 1. re-finding altered catalog photos
    refind = {"shifted": [0, 0, 0], "mirrored": [0, 0, 0]}  # top1, top3, total
    mirror_flagged = 0
    rows = []
    for p in catalog:
        im = Image.open(PHOTOS / p["image"]["path"]).convert("RGB")
        for kind, alt in (("shifted", shift_and_shrink(im)), ("mirrored", ImageOps.mirror(im))):
            dets = pipe.detector.detect(alt)
            if not dets:
                rows.append((p["slug"], kind, "no figure", "")); refind[kind][2] += 1
                continue
            figs = [FigureDetection(bbox=list(d.bbox), score=d.score) for d in dets]
            box = tuple(figs[pipe.pick(figs)].bbox)
            pose = build_pose(pipe.estimator.estimate(alt, box), profiles[p["profile"]], alt.size)
            q = PoseView(pose.keypoints, alt.width / alt.height)
            ranked = rank(q, by_profile[p["profile"]], profiles[p["profile"]])
            slugs = [r[0] for r in ranked]
            pos = slugs.index(p["slug"]) + 1
            refind[kind][0] += pos == 1
            refind[kind][1] += pos <= 3
            refind[kind][2] += 1
            if kind == "mirrored" and pos == 1 and ranked[0][2]:
                mirror_flagged += 1
            rows.append((p["slug"], kind, pos, f"{ranked[0][0]} ({ranked[0][1]:.2f})"))
        print(f"{p['slug']:20} " + "  ".join(f"{r[1]}=#{r[2]}" for r in rows[-2:]))

    # --- 2. stability: labeled vs predicted keypoints on eval_v1
    ds = ROOT / "ai-service" / "datasets" / "eval_v1"
    ann = json.loads((ds / "annotations.json").read_text(encoding="utf-8"))
    top1_same = overlap = n_stab = 0
    for img in ann["images"]:
        for g in img["figures"]:
            if "keypoints" not in g:
                continue
            im = Image.open(ds / "images" / img["file"]).convert("RGB")
            prof = profiles[g["profile"]]
            vis = {2: "visible", 1: "uncertain", 0: "not_visible"}
            gt = PoseView({n: Keypoint(x=x if v else None, y=y if v else None, confidence=1.0, visibility=vis[v])
                           for n, (x, y, v) in g["keypoints"].items()}, im.width / im.height)
            pred_pose = build_pose(pipe.estimator.estimate(im, tuple(g["bbox"])), prof, im.size)
            pred = PoseView(pred_pose.keypoints, im.width / im.height)
            a = [r[0] for r in rank(gt, by_profile[g["profile"]], prof)][:5]
            b = [r[0] for r in rank(pred, by_profile[g["profile"]], prof)][:5]
            n_stab += 1
            top1_same += a[0] == b[0]
            overlap += len(set(a) & set(b)) / 5

    # --- 3. feasibility of the catalog itself
    from app.services.pose_extractor import joint_angles
    warn = []
    for p in catalog:
        v = view_from_catalog(p)
        f = feasibility(joint_angles(v.keypoints, profiles[p["profile"]], v.aspect), profiles[p["profile"]])
        if f.warnings:
            warn.append((p["slug"], f.score, ", ".join(f"{w['joint']} {w['target']}° (limit {w['limit']}°)" for w in f.warnings)))

    # --- latency of matching a pose against the largest profile catalog
    biggest = max(by_profile.values(), key=len)
    q = view_from_catalog(biggest[0])
    t = time.perf_counter()
    for _ in range(50):
        rank(q, biggest, profiles[biggest[0]["profile"]])
    ms = (time.perf_counter() - t) * 1000 / 50

    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"  # noqa: E731
    md = ["# Sprint 5 matching evaluation", "", "Generated by `python -m eval.match_eval`. Matcher `match-0.1`.", "",
          f"Catalog: {len(catalog)} published poses ({', '.join(f'{k} {len(v)}' for k, v in by_profile.items())}).", "",
          "## Summary", "", "| Measure | Result |", "|---|---|"]
    for kind in ("shifted", "mirrored"):
        t1, t3, n = refind[kind]
        md.append(f"| Catalog photo {kind}: found at rank 1 / in top 3 | {t1}/{n} ({pct(t1, n)}) / {t3}/{n} ({pct(t3, n)}) |")
    md += [f"| Mirrored photo found first and flagged as mirrored | {mirror_flagged}/{refind['mirrored'][2]} |",
           f"| Same top pose from labeled vs predicted keypoints (eval_v1) | {top1_same}/{n_stab} ({pct(top1_same, n_stab)}) |",
           f"| Top-5 overlap, labeled vs predicted keypoints | {100 * overlap / n_stab:.0f}% |" if n_stab else "| Top-5 overlap | n/a |",
           f"| Catalog poses past an estimated joint limit | {len(warn)}/{len(catalog)} |",
           f"| Matching time, one pose vs {len(biggest)} candidates | {ms:.1f} ms |", "",
           "## Re-finding per pose (rank of the original; best match shown)", "",
           "| Pose | Change | Rank | Best match |", "|---|---|---:|---|"]
    md += [f"| {s} | {k} | {r} | {b} |" for s, k, r, b in rows]
    md += ["", "## Catalog poses past an estimated limit", "", "| Pose | Feasibility | Joints |", "|---|---:|---|"]
    md += [f"| {s} | {sc:.2f} | {w} |" for s, sc, w in warn] or ["| none | | |"]
    md += ["", "## Reading these numbers", "",
           "- Re-finding checks that matching is robust to framing and mirroring, not that recommendations are good taste.",
           "  Whether users like the suggested poses needs user testing (PRD success metric: ≥ 30% save a recommendation).",
           "- The catalog is small, so a pose has few close neighbours; scores will tighten as it grows.",
           "- Three eval_v1 photos (001, 003, 023) are also catalog photos, which flatters the stability numbers slightly.",
           "- Stability is the weak spot: many candidates score close together, so small keypoint errors reorder them.",
           "  Sprint 6 should rank by score bands and diversity rather than trusting small score differences.",
           "- Limits are estimated per profile, not measured per figure: a warning means \"check by hand\".", ""]
    out = ROOT / "ai-service" / "reports" / "match_v1.md"
    out.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print("\n".join(md[:16]))


if __name__ == "__main__":
    main()
