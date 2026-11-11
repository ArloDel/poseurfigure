from pathlib import Path

import pytest

from app.schemas.analysis import Keypoint
from app.services.pose_extractor import COCO17, RawPoint, map_to_profile
from app.services.pose_matcher import PoseView, feasibility, match, mirror
from app.services.profiles import load_profiles
from tests.fakes import STANDING

PROFILES = load_profiles(Path(__file__).resolve().parents[2] / "shared" / "skeleton_profiles")
H = PROFILES["humanoid_v1"]


def view(points: dict, aspect: float = 1.0, hidden: tuple = ()) -> PoseView:
    raw = [RawPoint(*points[n], 0.05 if n in hidden else 0.9) for n in COCO17]
    return PoseView(map_to_profile(raw, H), aspect)


# Right arm (on the photo's left) raised straight up; the rest like STANDING.
ARM_UP = dict(STANDING, right_elbow=(0.40, 0.10), right_wrist=(0.40, 0.0))
# Deep crouch.
CROUCH = dict(STANDING, left_knee=(0.62, 0.65), right_knee=(0.38, 0.65), left_ankle=(0.56, 0.78), right_ankle=(0.44, 0.78))


def test_identical_pose_scores_near_one():
    m = match(view(STANDING), view(STANDING), H)
    assert m.similarity > 0.99
    assert set(m.components) == {"angle", "position", "embedding"}
    assert m.mirrored is False


def test_same_pose_smaller_and_elsewhere_in_the_photo_still_matches():
    moved = {n: (0.1 + x * 0.4, 0.3 + y * 0.4) for n, (x, y) in STANDING.items()}
    assert match(view(STANDING), view(moved), H).similarity > 0.99


def test_similarity_falls_as_a_joint_moves_further():
    arm_out = dict(STANDING, right_elbow=(0.25, 0.25), right_wrist=(0.10, 0.25))  # right arm out to the side
    q = view(STANDING)
    s_out, s_up = match(q, view(arm_out), H).similarity, match(q, view(ARM_UP), H).similarity
    assert 0.99 > s_out > s_up


def test_one_big_change_and_several_moderate_ones_can_cost_the_same():
    # Averaging over joints: raising one arm fully is about as far from standing as a crouch.
    q = view(STANDING)
    assert match(q, view(ARM_UP), H).similarity == pytest.approx(match(q, view(CROUCH), H).similarity, abs=0.03)


def test_mirrored_pose_is_recognized():
    left_arm_up = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))
    m = match(view(left_arm_up), view(ARM_UP), H)
    assert m.mirrored is True
    assert m.similarity > 0.97


def test_mirror_swaps_sides_and_flips_x():
    m = mirror(view(ARM_UP))
    assert m.keypoints["left_wrist"].x == pytest.approx(0.60)
    assert m.keypoints["right_wrist"].x == pytest.approx(1 - 0.62)


def test_few_shared_joints_pull_similarity_toward_half():
    legs_hidden = ("left_knee", "right_knee", "left_ankle", "right_ankle", "left_wrist", "right_wrist", "left_elbow", "right_elbow")
    full = match(view(STANDING), view(STANDING), H)
    partial = match(view(STANDING, hidden=legs_hidden), view(STANDING), H)
    assert partial.shared_joints < full.shared_joints
    assert 0.5 < partial.similarity < full.similarity


def test_no_torso_means_no_position_score():
    m = match(view(STANDING, hidden=("left_hip", "right_hip")), view(STANDING), H)
    assert "position" not in m.components


def test_aspect_ratio_is_respected():
    # The same pose drawn in a 2:1 photo stretched to normalized coordinates is not a different pose.
    wide = {n: (0.25 + x * 0.5, y) for n, (x, y) in STANDING.items()}
    assert match(view(STANDING), view(wide, aspect=2.0), H).similarity > 0.99


def test_feasibility_within_limits_is_one():
    f = feasibility({"left_elbow": 90, "right_knee": 120, "left_shoulder": 160}, H)
    assert f.score == 1.0 and f.warnings == []


def test_feasibility_penalizes_joints_past_the_limit():
    f = feasibility({"left_elbow": 20, "right_knee": 120}, H)  # profile elbow min is 35
    assert f.warnings == [{"joint": "left_elbow", "target": 20, "limit": 35, "beyond_by": 15, "limit_source": "estimated"}]
    assert f.score == pytest.approx(0.7)


def test_one_impossible_joint_caps_the_score():
    f = feasibility({"left_elbow": 0, **{j: 120 for j in ("right_elbow", "left_knee", "right_knee", "left_hip", "right_hip")}}, H)
    assert f.score == pytest.approx(0.4)


def test_figure_limits_override_profile_limits():
    stiff = {"right_knee": {"min": 130, "max": 180}}
    f = feasibility({"right_knee": 100}, H, stiff)
    assert f.warnings[0]["limit_source"] == "figure"
    assert f.warnings[0]["limit"] == 130
    assert f.score < 1.0


def test_keypoint_model_copy_keeps_visibility():
    k = Keypoint(x=0.2, y=0.3, confidence=0.9, visibility="visible")
    assert k.model_copy(update={"x": 0.8}).visibility == "visible"
