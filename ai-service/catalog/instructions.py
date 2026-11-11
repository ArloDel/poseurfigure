"""Turns a pose's joint angles into structured, ordered instructions (PRD 13).

These describe the target pose itself. Instructions relative to the user's own figure
("bend 40 degrees more") come later, from the difference between two poses.
"""
from __future__ import annotations

import math

from app.schemas.analysis import Keypoint

# Joint order in the instructions: torso first, then arms, then legs (PRD 4.6).
ORDER = ["torso", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
         "left_hip", "right_hip", "left_knee", "right_knee"]


def _bend_or_straighten(angle: float) -> tuple[str, str]:
    if angle >= 160:
        return "straighten", "low"
    return "bend", "high" if angle < 110 else "medium"


def _shoulder(angle: float) -> tuple[str, str]:
    # Angle between torso and upper arm: ~0-20 arm down, 90 out to the side or forward, 180 straight up.
    if angle < 25:
        return "lower", "low"
    if angle > 150:
        return "raise_overhead", "high"
    return "raise", "high" if angle > 60 else "medium"


def _hip(angle: float) -> tuple[str, str]:
    # Angle between torso and thigh: 180 standing straight, 90 thigh level (sitting, high kick).
    if angle >= 165:
        return "straighten", "low"
    return "lift_leg", "high" if angle < 130 else "medium"


def torso_lean(kps: dict[str, Keypoint], aspect: float) -> float | None:
    """Degrees the neck-to-hips line leans away from vertical in the photo (2D)."""
    n, lh, rh = kps.get("neck"), kps.get("left_hip"), kps.get("right_hip")
    if not all(k is not None and k.visibility == "visible" for k in (n, lh, rh)):
        return None
    hx, hy = (lh.x + rh.x) / 2, (lh.y + rh.y) / 2
    dx, dy = (n.x - hx) * aspect, hy - n.y
    if dy <= 0:
        return None
    return math.degrees(math.atan2(abs(dx), dy))


def build_instructions(angles: dict[str, float], kps: dict[str, Keypoint], aspect: float) -> list[dict]:
    steps = []
    lean = torso_lean(kps, aspect)
    if lean is not None and lean >= 12:
        steps.append({"body_part": "torso", "movement": "lean", "target_angle": round(lean), "priority": "high" if lean > 25 else "medium"})
    for joint in ORDER[1:]:
        if joint not in angles:
            continue
        a = angles[joint]
        if joint.endswith("shoulder"):
            movement, priority = _shoulder(a)
        elif joint.endswith("_hip"):
            movement, priority = _hip(a)
        else:
            movement, priority = _bend_or_straighten(a)
        steps.append({"body_part": joint, "movement": movement, "target_angle": round(a), "priority": priority})
    for i, s in enumerate(steps, start=1):
        s["step"] = i
    return steps


def constraints(angles: dict[str, float], limits: dict[str, dict], margin: float = 5.0) -> dict[str, dict]:
    """Joints whose target is at or past the profile's estimated limit, so the app can warn (PRD 8.5)."""
    out = {}
    for joint, a in angles.items():
        lim = limits.get(joint)
        if lim and a <= lim["min"] + margin:
            out[joint] = {"target": round(a), "warn_above_profile_max": True, "limit": lim["min"], "source": lim.get("source", "estimated")}
    return out
