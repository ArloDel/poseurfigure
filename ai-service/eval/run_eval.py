"""Measure the Sprint 4 pipeline on a labeled eval set and write a report (PRD 16.2, 16.4).

usage (from ai-service/):  python -m eval.run_eval [--dataset datasets/eval_v1] [--out reports]

Each stage is measured on its own so errors don't mix:
- detection on the full photo,
- classification on the labeled box (not the detected one),
- keypoints on the labeled box,
plus end-to-end time per photo through the real pipeline.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.models.object_detector import iou
from app.services.image_quality import assess
from app.services.pipeline import Pipeline
from app.services.pose_extractor import build_pose
from app.services.profiles import load_profiles

IOU_MATCH = 0.5
PCK_ALPHAS = (0.05, 0.10)
DERIVED = {"neck", "chest", "waist", "head"}


def match(preds: list[tuple], gts: list[dict]) -> tuple[int, int, int, list[bool]]:
    """Greedy by score. Predictions on `ignore` regions are dropped. Returns tp, fp, fn, matched-per-gt."""
    real = [g for g in gts if not g.get("ignore")]
    ignored = [g for g in gts if g.get("ignore")]
    taken = [False] * len(real)
    tp = fp = 0
    for box, _score in sorted(preds, key=lambda p: p[1], reverse=True):
        best, best_iou = None, IOU_MATCH
        for i, g in enumerate(real):
            v = iou(box, g["bbox"])
            if not taken[i] and v >= best_iou:
                best, best_iou = i, v
        if best is not None:
            taken[best] = True
            tp += 1
        elif any(iou(box, g["bbox"]) >= IOU_MATCH * 0.6 for g in ignored):
            continue
        else:
            fp += 1
    return tp, fp, taken.count(False), taken


def crop(im: Image.Image, bbox) -> Image.Image:
    w, h = im.size
    return im.crop((bbox[0] * w, bbox[1] * h, bbox[2] * w, bbox[3] * h))


def pct(a: float, b: float) -> str:
    return f"{100 * a / b:.0f}%" if b else "n/a"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # the report uses ≥ and the Windows console defaults to cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="datasets/eval_v1")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    ds = Path(args.dataset)
    doc = json.loads((ds / "annotations.json").read_text(encoding="utf-8"))
    settings = get_settings()
    profiles = load_profiles(settings.skeleton_profiles_path)

    from app.main import build_pipeline

    t = time.perf_counter()
    pipe: Pipeline = build_pipeline()
    cls, est = pipe.classifier, pipe.estimator
    warm = Image.open(ds / "images" / doc["images"][0]["file"]).convert("RGB")
    pipe.run(warm, assess(warm, settings))
    load_s = time.perf_counter() - t

    tp = fp = fn = 0
    img_hit = img_pos = neg_clean = neg = pick_ok = 0
    confusion: Counter = Counter()
    conf_needed = conf_right = conf_total = 0
    kp_hits = {a: defaultdict(lambda: [0, 0]) for a in PCK_ALPHAS}
    vis_pred = Counter()
    swaps = swap_checks = 0
    e2e_right = e2e_total = 0
    latencies, per_image = [], []

    for img in doc["images"]:
        im = Image.open(ds / "images" / img["file"]).convert("RGB")
        w, h = im.size
        gts = img["figures"]
        real = [g for g in gts if not g.get("ignore")]

        # --- end-to-end latency through the real pipeline (quality check bypassed for small photos)
        t0 = time.perf_counter()
        quality = assess(im, settings).model_copy(update={"ok": True, "issues": []})
        run = pipe.run(im, quality)
        latencies.append((time.perf_counter() - t0) * 1000)

        # --- detection
        preds = [(f.bbox, f.score) for f in run.figures]
        img_tp, img_fp, img_fn, taken = match(preds, gts)
        tp, fp, fn = tp + img_tp, fp + img_fp, fn + img_fn
        # End-to-end type: what the user actually sees, from the detected box (photos with one profile only).
        gt_profiles = {g["profile"] for g in real}
        if len(gt_profiles) == 1 and run.classification is not None:
            e2e_total += 1
            e2e_right += run.classification.profile in gt_profiles
        if real:
            img_pos += 1
            main_gt = max(range(len(real)), key=lambda i: (real[i]["bbox"][2] - real[i]["bbox"][0]) * (real[i]["bbox"][3] - real[i]["bbox"][1]))
            img_hit += taken[main_gt]
            if run.figures:
                chosen = run.figures[Pipeline.pick(run.figures)].bbox
                pick_ok += any(iou(chosen, g["bbox"]) >= IOU_MATCH for g in real)
        else:
            neg += 1
            neg_clean += not run.figures

        # --- classification on labeled boxes
        for g in real:
            scores = cls.classify(crop(im, g["bbox"]))
            best = max(scores, key=scores.get)
            confusion[(g["profile"], best)] += 1
            conf_total += 1
            if scores[best] < settings.min_profile_confidence:
                conf_needed += 1
            else:
                conf_right += best == g["profile"]

        # --- keypoints on labeled boxes
        for g in real:
            if "keypoints" not in g:
                continue
            raw = est.estimate(im, tuple(g["bbox"]))
            pose = build_pose(raw, profiles[g["profile"]], (w, h))
            bw, bh = (g["bbox"][2] - g["bbox"][0]) * w, (g["bbox"][3] - g["bbox"][1]) * h
            scale = max(bw, bh)
            for name, (gx, gy, gv) in g["keypoints"].items():
                if gv != 2:
                    continue
                k = pose.keypoints[name]
                vis_pred[k.visibility] += 1
                d = math.hypot((k.x - gx) * w, (k.y - gy) * h) if k.x is not None else math.inf
                for a in PCK_ALPHAS:
                    kp_hits[a][name][1] += 1
                    kp_hits[a][name][0] += d <= a * scale
            # left/right swap: both sides labeled and predicted, and the swapped assignment fits better.
            for side_pair in (("left_wrist", "right_wrist"), ("left_ankle", "right_ankle"), ("left_elbow", "right_elbow")):
                l, r = side_pair
                gl, gr = g["keypoints"][l], g["keypoints"][r]
                pl, pr = pose.keypoints[l], pose.keypoints[r]
                if gl[2] == 2 and gr[2] == 2 and pl.x is not None and pr.x is not None:
                    swap_checks += 1
                    straight = math.dist((pl.x, pl.y), gl[:2]) + math.dist((pr.x, pr.y), gr[:2])
                    crossed = math.dist((pl.x, pl.y), gr[:2]) + math.dist((pr.x, pr.y), gl[:2])
                    swaps += crossed < straight * 0.7

        per_image.append({"file": img["file"], "figures": len(real), "detected": len(run.figures), "tp": img_tp, "fp": img_fp,
                          "profile": run.profile, "ms": round(latencies[-1])})

    # --- report
    prec, rec = (tp / (tp + fp) if tp + fp else 0), (tp / (tp + fn) if tp + fn else 0)
    labels = ["humanoid_v1", "anime_v1", "mecha_v1"]
    cls_correct = sum(confusion[(x, x)] for x in labels)

    def pck_rows(alpha):
        rows, tot = [], [0, 0]
        groups = {"direct joints": [0, 0], "derived (head, neck, chest, waist)": [0, 0]}
        for name in doc["keypoint_names"]:
            hit, n = kp_hits[alpha][name]
            tot[0] += hit; tot[1] += n
            grp = groups["derived (head, neck, chest, waist)" if name in DERIVED else "direct joints"]
            grp[0] += hit; grp[1] += n
            rows.append((name, hit, n))
        return rows, tot, groups

    rows10, tot10, groups10 = pck_rows(0.10)
    rows05, tot05, _ = pck_rows(0.05)
    n_kp_figs = sum(1 for i in doc["images"] for g in i["figures"] if "keypoints" in g)
    lat_sorted = sorted(latencies)
    p95 = lat_sorted[max(0, math.ceil(0.95 * len(lat_sorted)) - 1)]

    summary = {
        "dataset": doc["name"], "images": len(doc["images"]),
        "detection": {"precision": round(prec, 3), "recall": round(rec, 3), "tp": tp, "fp": fp, "fn": fn,
                      "main_figure_found": f"{img_hit}/{img_pos}", "photos_without_figures_clean": f"{neg_clean}/{neg}",
                      "picked_a_real_figure": f"{pick_ok}/{img_pos}"},
        "classification": {"accuracy": round(cls_correct / conf_total, 3) if conf_total else None,
                           "end_to_end": f"{e2e_right}/{e2e_total}",
                           "asks_confirmation": f"{conf_needed}/{conf_total}",
                           "accuracy_when_confident": round(conf_right / (conf_total - conf_needed), 3) if conf_total - conf_needed else None,
                           "confusion": {f"{t}->{p}": n for (t, p), n in sorted(confusion.items())}},
        "keypoints": {"figures": n_kp_figs, "visible_labels": tot10[1], "pck@0.10": round(tot10[0] / tot10[1], 3) if tot10[1] else None,
                      "pck@0.05": round(tot05[0] / tot05[1], 3) if tot05[1] else None,
                      "predicted_visibility_of_visible_labels": dict(vis_pred), "left_right_swaps": f"{swaps}/{swap_checks}"},
        "latency_ms": {"mean": round(statistics.mean(latencies)), "p50": round(statistics.median(latencies)), "p95": round(p95),
                       "model_load_and_first_run_s": round(load_s, 1)},
        "environment": {"machine": platform.machine(), "processor": platform.processor(), "cpus": os.cpu_count(),
                        "python": platform.python_version(), "models": pipe.models, "pipeline": pipe.version},
        "per_image": per_image,
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{doc['name']}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8", newline="\n")

    det_s, cls_s, kp_s, lat = summary["detection"], summary["classification"], summary["keypoints"], summary["latency_ms"]
    md = [f"# Sprint 4 evaluation: {doc['name']}", "",
          f"Generated by `python -m eval.run_eval`. Pipeline `{pipe.version}`.", "",
          "Small, hand-labeled, single-labeler set (see `datasets/eval_v1/README.md`). Use these numbers to compare",
          "approaches and catch regressions, not as production accuracy.", "",
          "## Summary", "",
          "| Measure | Result | PRD target |", "|---|---|---|",
          f"| Main figure found in photos with figures | {det_s['main_figure_found']} ({pct(img_hit, img_pos)}) | ≥ 85% detection success |",
          f"| Detection precision / recall (IoU ≥ {IOU_MATCH}) | {prec:.0%} / {rec:.0%} ({tp} hits, {fp} false, {fn} missed) | |",
          f"| Photos without figures left empty | {det_s['photos_without_figures_clean']} | |",
          f"| Figure type correct (on labeled boxes) | {cls_correct}/{conf_total} ({pct(cls_correct, conf_total)}) | |",
          f"| Figure type correct end to end (detected box, what the user sees) | {e2e_right}/{e2e_total} ({pct(e2e_right, e2e_total)}) | |",
          f"| Type asks the user to confirm (confidence < {settings.min_profile_confidence}) | {cls_s['asks_confirmation']} | FIG-03 |",
          f"| Keypoints within 10% of figure size (PCK@0.1) | {tot10[0]}/{tot10[1]} ({pct(*tot10)}) | measured prototype |",
          f"| Keypoints within 5% (PCK@0.05) | {tot05[0]}/{tot05[1]} ({pct(*tot05)}) | |",
          f"| Left/right swapped (wrists, elbows, ankles) | {kp_s['left_right_swaps']} | |",
          f"| Time per photo, CPU (mean / p95) | {lat['mean']} ms / {lat['p95']} ms | ≤ 15 s |", "",
          "## Figure type confusion (rows: labeled, columns: predicted)", "",
          "| | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    for t_ in labels:
        md.append(f"| {t_} | " + " | ".join(str(confusion[(t_, p_)]) for p_ in labels) + " |")
    md += ["", "## Keypoints per joint (PCK@0.1 on visible labels)", "", "| Joint | Hit | Labeled | PCK |", "|---|---:|---:|---:|"]
    for name, hit, n in rows10:
        md.append(f"| {name} | {hit} | {n} | {pct(hit, n)} |")
    md += ["", "| Group | PCK@0.1 |", "|---|---:|"]
    for gname, (hit, n) in groups10.items():
        md.append(f"| {gname} | {pct(hit, n)} ({hit}/{n}) |")
    md += ["", f"Predicted visibility of joints labeled visible: {dict(vis_pred)}.", "",
           "## Per photo", "", "| Photo | Figures | Detected | Hits | False | Type | ms |", "|---|---:|---:|---:|---:|---|---:|"]
    for r in per_image:
        md.append(f"| {r['file']} | {r['figures']} | {r['detected']} | {r['tp']} | {r['fp']} | {r['profile'] or '-'} | {r['ms']} |")
    md += ["", "## Environment", "", f"- CPU: {summary['environment']['processor'] or summary['environment']['machine']}, {os.cpu_count()} threads",
           f"- Python {platform.python_version()}", f"- Models: {pipe.models}",
           f"- Model load + first run: {lat['model_load_and_first_run_s']} s", ""]
    (out / f"{doc['name']}.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print("\n".join(md[:22]))


if __name__ == "__main__":
    main()
