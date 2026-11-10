"""Source of truth for eval_v1 labels. Run to regenerate annotations.json.

Labels were made by hand on a 5% coordinate grid, so expect roughly +/-2% error.
Conventions:
- Coordinates are normalized to the image: x, y in 0..1, origin top-left.
- bbox = [x0, y0, x1, y1] around the figure itself: hair and wings included,
  held props (swords, rifles, shields), stands and bases excluded.
- left/right are the FIGURE's own sides (as in COCO). On a figure facing the camera,
  its left arm appears on the right side of the photo.
- Keypoint visibility: 2 = visible, 1 = hidden but position is clear (inside a coat,
  behind the body), 0 = not labeled (out of frame or position unknown). Only v=2 points
  are used for accuracy; hidden joints are never guessed.
- ignore = blurry background figures or pictures of robots on posters: detections
  there count neither as hits nor as false positives.
"""
import json
from pathlib import Path

NAMES = ["head", "neck", "chest", "waist", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
         "left_wrist", "right_wrist", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]


def kp(**points):
    """kp(head=(x, y), neck=(x, y, 1), ...) -> {name: [x, y, v]}; unlisted names get v=0."""
    out = {}
    for n in NAMES:
        p = points.get(n)
        out[n] = [0.0, 0.0, 0] if p is None else [p[0], p[1], p[2] if len(p) > 2 else 2]
    return out


def fig(profile, bbox, keypoints=None, ignore=False):
    f = {"profile": profile, "bbox": bbox}
    if keypoints:
        f["keypoints"] = keypoints
    if ignore:
        f["ignore"] = True
    return f


H, A, M = "humanoid_v1", "anime_v1", "mecha_v1"

LABELS = {
    "001.jpg": [fig(H, [0.01, 0.0, 0.98, 0.99], kp(
        head=(0.42, 0.13), neck=(0.43, 0.23), chest=(0.45, 0.32), waist=(0.49, 0.47),
        right_shoulder=(0.32, 0.27), right_elbow=(0.30, 0.38), right_wrist=(0.22, 0.38),
        left_shoulder=(0.62, 0.25), left_elbow=(0.74, 0.32), left_wrist=(0.77, 0.22),
        right_hip=(0.40, 0.53), left_hip=(0.57, 0.52), right_knee=(0.17, 0.64), left_knee=(0.63, 0.63),
        right_ankle=(0.19, 0.85), left_ankle=(0.86, 0.90)))],
    "002.jpg": [fig(H, [0.01, 0.0, 0.82, 1.0], kp(
        head=(0.50, 0.11), neck=(0.52, 0.22), chest=(0.52, 0.32), waist=(0.52, 0.47),
        right_shoulder=(0.28, 0.22), right_elbow=(0.24, 0.37), right_wrist=(0.20, 0.44),
        left_shoulder=(0.78, 0.25), left_elbow=(0.86, 0.45), left_wrist=(0.80, 0.56),
        right_hip=(0.40, 0.52), left_hip=(0.62, 0.53), right_knee=(0.29, 0.62), left_knee=(0.63, 0.77),
        right_ankle=(0.25, 0.73), left_ankle=(0.66, 0.90)))],
    "003.jpg": [fig(H, [0.22, 0.27, 0.80, 1.0], kp(
        head=(0.53, 0.43), neck=(0.51, 0.55), chest=(0.48, 0.75),
        right_shoulder=(0.41, 0.58), right_wrist=(0.29, 0.73),
        left_shoulder=(0.55, 0.66), left_elbow=(0.67, 0.71), left_wrist=(0.76, 0.74)))],
    "004.jpg": [fig(H, [0.28, 0.11, 0.77, 1.0], kp(
        head=(0.49, 0.30), neck=(0.49, 0.44), chest=(0.50, 0.55), waist=(0.49, 0.83),
        right_shoulder=(0.38, 0.50), right_elbow=(0.35, 0.72), right_wrist=(0.47, 0.71),
        left_shoulder=(0.66, 0.50), left_elbow=(0.70, 0.70), left_wrist=(0.60, 0.60),
        right_hip=(0.42, 0.92, 1), left_hip=(0.58, 0.92, 1)))],
    "005.jpg": [fig(H, [0.39, 0.06, 0.62, 0.92], kp(
        head=(0.51, 0.12), neck=(0.51, 0.20), chest=(0.51, 0.30), waist=(0.51, 0.50),
        right_shoulder=(0.46, 0.24), right_elbow=(0.45, 0.34), right_wrist=(0.56, 0.27, 1),
        left_shoulder=(0.57, 0.24), left_elbow=(0.58, 0.34), left_wrist=(0.46, 0.27, 1),
        right_hip=(0.48, 0.53), left_hip=(0.54, 0.53), right_knee=(0.46, 0.70), left_knee=(0.53, 0.70),
        right_ankle=(0.44, 0.88), left_ankle=(0.54, 0.88)))],
    "007.jpg": [fig(H, [0.15, 0.12, 0.75, 0.86], kp(
        head=(0.54, 0.25), neck=(0.55, 0.32), chest=(0.54, 0.39), waist=(0.52, 0.48),
        right_shoulder=(0.44, 0.33), right_elbow=(0.34, 0.40), right_wrist=(0.27, 0.43),
        left_shoulder=(0.66, 0.31), left_elbow=(0.68, 0.38), left_wrist=(0.69, 0.41),
        right_hip=(0.47, 0.55), left_hip=(0.61, 0.56), right_knee=(0.42, 0.65), left_knee=(0.61, 0.66),
        right_ankle=(0.41, 0.75), left_ankle=(0.64, 0.84)))],
    "008.jpg": [fig(H, [0.26, 0.10, 0.65, 1.0], kp(
        head=(0.52, 0.20), neck=(0.52, 0.29), chest=(0.52, 0.38), waist=(0.53, 0.50),
        right_shoulder=(0.44, 0.33), right_elbow=(0.38, 0.38), right_wrist=(0.33, 0.31),
        left_shoulder=(0.61, 0.34), left_elbow=(0.63, 0.46), left_wrist=(0.62, 0.55),
        right_hip=(0.47, 0.58), left_hip=(0.58, 0.59), right_knee=(0.46, 0.78), left_knee=(0.58, 0.80),
        right_ankle=(0.45, 0.96), left_ankle=(0.53, 0.92)))],
    "009.jpg": [fig(H, [0.33, 0.10, 0.67, 0.92], kp(
        head=(0.50, 0.18), neck=(0.50, 0.26), chest=(0.51, 0.32), waist=(0.51, 0.41),
        right_shoulder=(0.44, 0.29), right_elbow=(0.43, 0.40), right_wrist=(0.39, 0.49),
        left_shoulder=(0.57, 0.29), left_elbow=(0.59, 0.28, 1), left_wrist=(0.63, 0.20),
        right_hip=(0.47, 0.46, 1), left_hip=(0.55, 0.46, 1), right_ankle=(0.42, 0.88, 1), left_ankle=(0.57, 0.88, 1)))],
    "010.jpg": [fig(H, [0.27, 0.30, 0.43, 0.71], kp(
        head=(0.345, 0.33), neck=(0.35, 0.37), chest=(0.35, 0.42), waist=(0.35, 0.52, 1),
        right_shoulder=(0.31, 0.39), right_elbow=(0.29, 0.46), right_wrist=(0.275, 0.49),
        left_shoulder=(0.39, 0.39), left_elbow=(0.395, 0.44), left_wrist=(0.41, 0.37),
        right_hip=(0.33, 0.55, 1), left_hip=(0.37, 0.55, 1), right_knee=(0.33, 0.63, 1), left_knee=(0.37, 0.63, 1),
        right_ankle=(0.32, 0.69), left_ankle=(0.37, 0.69)))],
    # Back view: the figure's left side is on the left of the photo.
    "011.jpg": [fig(H, [0.11, 0.06, 0.33, 1.0], kp(
        head=(0.21, 0.09), neck=(0.22, 0.17), chest=(0.22, 0.30, 1), waist=(0.23, 0.48, 1),
        left_shoulder=(0.14, 0.25), right_shoulder=(0.28, 0.24), right_elbow=(0.31, 0.42), right_wrist=(0.33, 0.55),
        left_elbow=(0.13, 0.43), left_wrist=(0.15, 0.58, 1), left_hip=(0.18, 0.60, 1), right_hip=(0.27, 0.60, 1)))],
    "012.jpg": [fig(H, [0.17, 0.06, 0.86, 0.91], kp(
        head=(0.50, 0.20), neck=(0.50, 0.30), chest=(0.50, 0.38), waist=(0.50, 0.50),
        right_shoulder=(0.32, 0.35), right_elbow=(0.27, 0.46), right_wrist=(0.21, 0.53),
        left_shoulder=(0.69, 0.36), left_elbow=(0.73, 0.46), left_wrist=(0.80, 0.55),
        right_hip=(0.40, 0.58), left_hip=(0.62, 0.58), right_knee=(0.42, 0.71), left_knee=(0.65, 0.71),
        right_ankle=(0.43, 0.83), left_ankle=(0.66, 0.82)))],
    "013.jpg": [fig(H, [0.36, 0.01, 0.67, 0.74], kp(
        head=(0.51, 0.13), neck=(0.51, 0.19), chest=(0.51, 0.25), waist=(0.51, 0.33),
        right_shoulder=(0.44, 0.23), right_elbow=(0.42, 0.31), right_wrist=(0.40, 0.38),
        left_shoulder=(0.59, 0.23), left_elbow=(0.62, 0.31), left_wrist=(0.64, 0.38),
        right_hip=(0.47, 0.43), left_hip=(0.56, 0.43), right_knee=(0.47, 0.58), left_knee=(0.57, 0.58),
        right_ankle=(0.47, 0.72), left_ankle=(0.59, 0.72)))],
    "014.jpg": [fig(H, [0.07, 0.10, 0.34, 1.0]), fig(H, [0.64, 0.12, 0.94, 1.0])],
    "015.jpg": [fig(H, b) for b in ([0.04, 0.19, 0.23, 0.97], [0.17, 0.21, 0.31, 0.97], [0.24, 0.17, 0.43, 0.98],
                                    [0.39, 0.17, 0.60, 0.98], [0.53, 0.18, 0.67, 0.95], [0.56, 0.15, 0.82, 0.98],
                                    [0.70, 0.12, 0.97, 0.96])],
    "016.jpg": [fig(H, [0.08, 0.22, 0.43, 1.0]), fig(H, [0.32, 0.13, 0.65, 1.0]), fig(H, [0.65, 0.18, 0.89, 1.0])],
    "017.jpg": [fig(H, b) for b in ([0.18, 0.16, 0.44, 0.84], [0.40, 0.17, 0.62, 0.80], [0.53, 0.20, 0.80, 0.83],
                                    [0.71, 0.24, 0.98, 0.83])],
    "018.jpg": [fig(A, [0.10, 0.0, 0.90, 0.98], kp(
        head=(0.47, 0.13), neck=(0.47, 0.23), chest=(0.50, 0.34), waist=(0.53, 0.52),
        right_shoulder=(0.33, 0.31), right_elbow=(0.26, 0.50), right_wrist=(0.24, 0.66),
        left_shoulder=(0.60, 0.32), left_elbow=(0.73, 0.50, 1), left_wrist=(0.82, 0.66),
        right_hip=(0.45, 0.62), left_hip=(0.64, 0.62), right_knee=(0.57, 0.95), left_knee=(0.86, 0.82),
        right_ankle=(0.20, 0.78, 1)))],
    # Side view facing right: the figure's right side faces the camera.
    "019.jpg": [fig(A, [0.30, 0.03, 0.83, 1.0], kp(
        head=(0.65, 0.12), neck=(0.63, 0.20), chest=(0.65, 0.32), waist=(0.60, 0.50),
        right_shoulder=(0.60, 0.27), right_elbow=(0.58, 0.45), right_wrist=(0.72, 0.55),
        right_hip=(0.58, 0.60), right_knee=(0.55, 0.78), right_ankle=(0.50, 0.97), left_ankle=(0.40, 0.98, 1)))],
    "020.jpg": [fig(A, [0.13, 0.02, 0.65, 0.94]), fig(A, [0.47, 0.06, 0.88, 0.95])],
    # Twisted pose: arms too ambiguous to label, box only.
    "021.jpg": [fig(A, [0.25, 0.03, 0.82, 0.98])],
    "022.jpg": [fig(A, [0.55, 0.02, 0.82, 1.0], kp(
        head=(0.65, 0.20), neck=(0.66, 0.29), chest=(0.67, 0.37), waist=(0.68, 0.46),
        right_shoulder=(0.62, 0.33), right_elbow=(0.62, 0.42, 1), right_wrist=(0.58, 0.39),
        left_shoulder=(0.73, 0.32), left_elbow=(0.77, 0.36), left_wrist=(0.74, 0.23),
        right_hip=(0.64, 0.55, 1), left_hip=(0.71, 0.55, 1), right_knee=(0.67, 0.63), left_knee=(0.72, 0.72),
        right_ankle=(0.64, 0.68, 1), left_ankle=(0.74, 0.92)))],
    "023.jpg": [fig(A, [0.13, 0.08, 0.82, 0.98], kp(
        head=(0.55, 0.17), neck=(0.56, 0.25), chest=(0.57, 0.33), waist=(0.58, 0.44),
        right_shoulder=(0.44, 0.30), right_elbow=(0.38, 0.40), right_wrist=(0.27, 0.45),
        left_shoulder=(0.66, 0.29), left_elbow=(0.66, 0.38), left_wrist=(0.68, 0.44),
        right_hip=(0.50, 0.53), left_hip=(0.62, 0.53), right_knee=(0.43, 0.72), left_knee=(0.66, 0.72),
        right_ankle=(0.40, 0.90), left_ankle=(0.66, 0.92)))],
    "024.jpg": [fig(A, [0.07, 0.12, 0.76, 0.82], kp(
        head=(0.42, 0.22), neck=(0.43, 0.29), chest=(0.43, 0.36), waist=(0.43, 0.44),
        right_shoulder=(0.35, 0.33), right_elbow=(0.33, 0.42, 1), right_wrist=(0.48, 0.38, 1),
        left_shoulder=(0.50, 0.32), left_elbow=(0.58, 0.33), left_wrist=(0.68, 0.35),
        right_hip=(0.38, 0.52), left_hip=(0.48, 0.52), right_knee=(0.35, 0.66), left_knee=(0.55, 0.67),
        right_ankle=(0.28, 0.78), left_ankle=(0.63, 0.79)))],
    "025.jpg": [fig(A, [0.08, 0.04, 0.82, 1.0], kp(
        head=(0.45, 0.33), neck=(0.45, 0.40), chest=(0.44, 0.47), waist=(0.45, 0.56),
        right_shoulder=(0.38, 0.42), right_elbow=(0.30, 0.49), right_wrist=(0.29, 0.55),
        left_shoulder=(0.52, 0.42), left_elbow=(0.60, 0.49), left_wrist=(0.71, 0.55),
        right_hip=(0.40, 0.63), left_hip=(0.50, 0.63), right_knee=(0.37, 0.80), left_knee=(0.50, 0.79),
        right_ankle=(0.27, 0.68), left_ankle=(0.55, 0.97)))],
    "026.jpg": [fig(A, [0.20, 0.05, 0.53, 0.92]), fig(A, [0.53, 0.08, 0.90, 0.93])],
    "027.jpg": [fig(M, [0.13, 0.13, 0.84, 1.0]), fig(M, [0.78, 0.18, 1.0, 1.0], ignore=True),
                fig(M, [0.0, 0.0, 0.25, 0.40], ignore=True), fig(M, [0.47, 0.0, 0.75, 0.30], ignore=True)],
    "028.jpg": [fig(M, [0.43, 0.09, 0.80, 1.0])],
    "029.jpg": [fig(M, [0.22, 0.31, 0.88, 0.87])],
    "030.jpg": [fig(M, [0.20, 0.15, 0.60, 0.99]), fig(M, [0.67, 0.12, 0.92, 0.93])],
    "031.jpg": [fig(M, [0.25, 0.21, 0.92, 0.83])],
    "032.jpg": [fig(M, [0.30, 0.35, 0.76, 0.83])],
    "033.jpg": [fig(M, [0.09, 0.20, 0.94, 0.93])],
    "034.jpg": [fig(M, [0.11, 0.24, 0.51, 0.92]), fig(M, [0.45, 0.21, 0.91, 0.92])],
    "035.jpg": [fig(M, [0.27, 0.0, 0.79, 1.0]), fig(M, [0.60, 0.0, 1.0, 0.80], ignore=True)],
    # No figures: two show real people, which must not be detected as figures.
    "036.jpg": [], "037.jpg": [], "038.jpg": [], "039.jpg": [],
}


def main() -> None:
    here = Path(__file__).parent
    sources = {s["file"]: s for s in json.loads((here / "sources.json").read_text(encoding="utf-8"))}
    images = []
    for name, figures in LABELS.items():
        s = sources[name]
        images.append({"file": name, "width": s["width"], "height": s["height"], "figures": figures})
    doc = {
        "name": "eval_v1",
        "description": "Evaluation-only set: 38 CC-licensed photos of action figures and 4 without. Not for training.",
        "keypoint_names": NAMES,
        "labeling": "Hand-labeled on a 5% grid; see build_annotations.py for conventions.",
        "images": images,
    }
    (here / "annotations.json").write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
    n_fig = sum(len([f for f in i["figures"] if not f.get("ignore")]) for i in images)
    n_kp = sum(1 for i in images for f in i["figures"] if "keypoints" in f)
    print(f"{len(images)} images, {n_fig} figures, {n_kp} with keypoints")


if __name__ == "__main__":
    main()
