from app.schemas.analysis import Keypoint
from catalog.instructions import build_instructions, constraints, torso_lean


def kp(x, y, vis="visible"):
    return Keypoint(x=x, y=y, confidence=0.9, visibility=vis)


UPRIGHT = {"neck": kp(0.5, 0.2), "left_hip": kp(0.55, 0.6), "right_hip": kp(0.45, 0.6)}
LEANING = {"neck": kp(0.7, 0.2), "left_hip": kp(0.55, 0.6), "right_hip": kp(0.45, 0.6)}


def test_steps_are_ordered_torso_arms_legs_and_numbered():
    angles = {"right_knee": 95, "left_elbow": 170, "right_shoulder": 160, "left_hip": 120}
    steps = build_instructions(angles, LEANING, 1.0)

    assert [s["body_part"] for s in steps] == ["torso", "right_shoulder", "left_elbow", "left_hip", "right_knee"]
    assert [s["step"] for s in steps] == [1, 2, 3, 4, 5]


def test_movements_and_priorities_follow_the_angle():
    steps = {s["body_part"]: s for s in build_instructions(
        {"left_elbow": 170, "right_elbow": 90, "left_shoulder": 10, "right_shoulder": 160, "left_hip": 175, "right_hip": 100},
        UPRIGHT, 1.0)}

    assert (steps["left_elbow"]["movement"], steps["left_elbow"]["priority"]) == ("straighten", "low")
    assert (steps["right_elbow"]["movement"], steps["right_elbow"]["priority"]) == ("bend", "high")
    assert steps["left_shoulder"]["movement"] == "lower"
    assert steps["right_shoulder"]["movement"] == "raise_overhead"
    assert steps["left_hip"]["movement"] == "straighten"
    assert (steps["right_hip"]["movement"], steps["right_hip"]["priority"]) == ("lift_leg", "high")
    assert "torso" not in steps  # upright: no lean step


def test_torso_lean_needs_visible_anchors():
    assert torso_lean(UPRIGHT, 1.0) == 0
    assert round(torso_lean(LEANING, 1.0)) == 27
    assert torso_lean({**UPRIGHT, "neck": kp(None, None, "not_visible")}, 1.0) is None


def test_constraints_flag_targets_at_or_past_the_limit():
    limits = {"left_elbow": {"min": 35, "max": 180, "source": "estimated"}, "right_knee": {"min": 45, "max": 180}}
    out = constraints({"left_elbow": 38, "right_knee": 120}, limits)

    assert out == {"left_elbow": {"target": 38, "warn_above_profile_max": True, "limit": 35, "source": "estimated"}}
