"""Turns raw COCO-17 keypoints into a profile's skeleton, joint angles and a matching embedding.

Pure geometry, no model code, so it is fully unit-tested.
Conventions follow shared/skeleton_profiles: left/right are the figure's own sides,
angles are interior angles in the 2D image plane (180 = straight).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.analysis import Keypoint, PoseResult, SkeletonProfile

COCO17 = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
    "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
]
_FACE = ["nose", "left_eye", "right_eye", "left_ear", "right_ear"]
# Profile joints that are COCO joints with the same name.
_DIRECT = [n for n in COCO17 if n not in _FACE]

EMBEDDING_VERSION = "geo-v1"


@dataclass(frozen=True)
class RawPoint:
    x: float  # normalized image coordinates
    y: float
    score: float


@dataclass(frozen=True)
class Thresholds:
    visible: float = 0.5
    uncertain: float = 0.3


# Where chest and waist sit on the line from the neck (0) to the hip centre (1).
CHEST_T = 0.30
WAIST_T = 0.80


def _visibility(score: float, th: Thresholds) -> str:
    if score >= th.visible:
        return "visible"
    if score >= th.uncertain:
        return "uncertain"
    return "not_visible"


def _kp(p: RawPoint | None, th: Thresholds, source: str = "direct") -> Keypoint:
    if p is None:
        return Keypoint(x=None, y=None, confidence=0.0, visibility="not_visible", source="none")
    vis = _visibility(p.score, th)
    if vis == "not_visible":
        return Keypoint(x=None, y=None, confidence=round(p.score, 3), visibility=vis, source=source)
    return Keypoint(x=round(p.x, 4), y=round(p.y, 4), confidence=round(p.score, 3), visibility=vis, source=source)


def _mid(a: RawPoint, b: RawPoint) -> RawPoint:
    return RawPoint((a.x + b.x) / 2, (a.y + b.y) / 2, min(a.score, b.score))


def _lerp(a: RawPoint, b: RawPoint, t: float) -> RawPoint:
    return RawPoint(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, min(a.score, b.score))


def _head(coco: dict[str, RawPoint], th: Thresholds) -> RawPoint | None:
    face = [coco[n] for n in _FACE if n in coco and coco[n].score >= th.uncertain]
    if not face:
        return None
    w = sum(p.score for p in face)
    return RawPoint(sum(p.x * p.score for p in face) / w, sum(p.y * p.score for p in face) / w, max(p.score for p in face))


def map_to_profile(coco_points: list[RawPoint], profile: SkeletonProfile, th: Thresholds = Thresholds()) -> dict[str, Keypoint]:
    """COCO-17 (in COCO order) -> every keypoint the profile defines.

    Profile-only landmarks the model can't see (mecha backpack, shoulder armor) come back as
    `not_estimated` instead of a guess.
    """
    if len(coco_points) != len(COCO17):
        raise ValueError(f"expected {len(COCO17)} COCO keypoints, got {len(coco_points)}")
    coco = dict(zip(COCO17, coco_points))
    ok = lambda n: coco[n].score >= th.uncertain  # noqa: E731

    neck = _mid(coco["left_shoulder"], coco["right_shoulder"]) if ok("left_shoulder") and ok("right_shoulder") else None
    hipc = _mid(coco["left_hip"], coco["right_hip"]) if ok("left_hip") and ok("right_hip") else None

    out: dict[str, Keypoint] = {}
    for name in profile.keypoints:
        if name in _DIRECT:
            out[name] = _kp(coco[name], th)
        elif name == "head":
            out[name] = _kp(_head(coco, th), th)
        elif name == "neck":
            out[name] = _kp(neck, th, "derived")
        elif name in ("chest", "waist"):
            t = CHEST_T if name == "chest" else WAIST_T
            out[name] = _kp(_lerp(neck, hipc, t) if neck and hipc else None, th, "derived")
        else:
            out[name] = Keypoint(x=None, y=None, confidence=0.0, visibility="not_estimated", source="none")
    return out


def interior_angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], aspect: float = 1.0) -> float | None:
    """Angle ABC in degrees. `aspect` = width/height, so normalized coordinates are measured in real proportions."""
    v1 = ((a[0] - b[0]) * aspect, a[1] - b[1])
    v2 = ((c[0] - b[0]) * aspect, c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return None
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def joint_angles(kps: dict[str, Keypoint], profile: SkeletonProfile, aspect: float) -> dict[str, float]:
    angles = {}
    for joint, cfg in profile.joints.items():
        a, b, c = (kps.get(n) for n in cfg["segments"])
        if all(k is not None and k.visibility == "visible" for k in (a, b, c)):
            ang = interior_angle((a.x, a.y), (b.x, b.y), (c.x, c.y), aspect)
            if ang is not None:
                angles[joint] = round(ang, 1)
    return angles


def orientation(coco_points: list[RawPoint], aspect: float, th: Thresholds = Thresholds()) -> str:
    """Rough camera view from 2D cues (PRD POSE-05, estimate only)."""
    coco = dict(zip(COCO17, coco_points))
    ls, rs, lh, rh = (coco[n] for n in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"))
    if min(ls.score, rs.score) < th.uncertain:
        return "unknown"
    face = max(coco[n].score for n in ("nose", "left_eye", "right_eye"))
    width = abs(ls.x - rs.x) * aspect
    torso = math.hypot((ls.x + rs.x - lh.x - rh.x) / 2 * aspect, (ls.y + rs.y - lh.y - rh.y) / 2) if min(lh.score, rh.score) >= th.uncertain else 0
    if torso and width / torso < 0.35:
        return "side"
    if face < th.uncertain:
        return "back"
    # Facing the camera, the figure's left shoulder appears on the right of the photo.
    return "front" if ls.x > rs.x else "back"


def embedding(kps: dict[str, Keypoint], profile: SkeletonProfile, aspect: float) -> list[float]:
    """Position- and scale-free pose vector for catalog matching (Sprint 5).

    Per profile keypoint: (dx, dy, present). Centered on the hip centre (or neck), scaled by torso length,
    so the same pose at a different size or place in the photo gives the same vector.
    """
    def pt(n):
        k = kps.get(n)
        return (k.x * aspect, k.y) if k is not None and k.x is not None and k.visibility == "visible" else None

    lh, rh, neck = pt("left_hip"), pt("right_hip"), pt("neck")
    center = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2) if lh and rh else neck
    scale = math.dist(center, neck) if center and neck and center != neck else None
    if center is None or not scale:
        return [0.0] * (3 * len(profile.keypoints))

    vec: list[float] = []
    for n in profile.keypoints:
        p = pt(n)
        vec += [round((p[0] - center[0]) / scale, 4), round((p[1] - center[1]) / scale, 4), 1.0] if p else [0.0, 0.0, 0.0]
    return vec


def build_pose(coco_points: list[RawPoint], profile: SkeletonProfile, image_size: tuple[int, int],
               th: Thresholds = Thresholds()) -> PoseResult:
    aspect = image_size[0] / image_size[1]
    kps = map_to_profile(coco_points, profile, th)
    estimable = [n for n, k in kps.items() if k.visibility != "not_estimated"]
    return PoseResult(
        profile=profile.profile,
        keypoints=kps,
        joint_angles=joint_angles(kps, profile, aspect),
        orientation=orientation(coco_points, aspect, th),
        embedding=embedding(kps, profile, aspect),
        embedding_version=EMBEDDING_VERSION,
        visible_count=sum(1 for n in estimable if kps[n].visibility == "visible"),
        hidden=[n for n in estimable if kps[n].visibility != "visible"],
    )
