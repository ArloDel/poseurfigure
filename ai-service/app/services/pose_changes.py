"""Instructions relative to the user's own figure (PRD 4.6, 13): what to change to get from here to the target.

The catalog's instructions describe the target pose ("bend the right knee to 125 degrees"). These describe
the difference ("bend the right knee about 40 degrees more") and leave out joints that are already close.

Angles are the profile's interior angles in the 2D image plane (180 = straight), the same convention as the
catalog. Joint names are the user's own figure's: when the match is mirrored, the target is mirrored first.
A joint the photo doesn't show is listed as "unknown", so the app falls back to the catalog step for it.
"""
from __future__ import annotations

from app.services.pose_matcher import PoseView, mirror

# Torso first, then arms, then legs, like the catalog steps.
ORDER = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
         "left_hip", "right_hip", "left_knee", "right_knee"]
# Differences below this are within keypoint noise: the joint is already right.
KEEP_TOLERANCE = 12.0


def _action(joint: str, delta: float) -> str:
    """delta = target - current. Interior angles: smaller means more bent (or arm lower, leg lifted)."""
    if joint.endswith("shoulder"):
        return "raise" if delta > 0 else "lower"
    if joint.endswith("_hip"):
        # 180 is standing straight; a smaller hip angle lifts the thigh.
        return "lower_leg" if delta > 0 else "lift_leg"
    return "straighten" if delta > 0 else "bend"


def _priority(size: float) -> str:
    if size >= 45:
        return "high"
    return "medium" if size >= 20 else "low"


def changes(current: PoseView, target: PoseView, mirrored: bool) -> list[dict]:
    """One entry per joint the target defines, in step order. `current` and `target` need their angles set."""
    goal = mirror(target).angles if mirrored else target.angles
    out = []
    for joint in ORDER:
        if joint not in goal:
            continue
        t = goal[joint]
        c = current.angles.get(joint)
        if c is None:
            out.append({"joint": joint, "action": "unknown", "target": round(t), "current": None, "delta": None})
            continue
        delta = t - c
        if abs(delta) < KEEP_TOLERANCE:
            out.append({"joint": joint, "action": "keep", "target": round(t), "current": round(c), "delta": round(delta)})
            continue
        out.append({"joint": joint, "action": _action(joint, delta), "target": round(t), "current": round(c),
                    "delta": round(delta), "priority": _priority(abs(delta))})
    return out
