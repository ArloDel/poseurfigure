from pathlib import Path

import pytest

from app.services.pose_extractor import COCO17, RawPoint, build_pose, embedding, interior_angle, map_to_profile
from app.services.profiles import load_profiles

PROFILES = load_profiles(Path(__file__).resolve().parents[2] / "shared" / "skeleton_profiles")
HUMANOID, MECHA = PROFILES["humanoid_v1"], PROFILES["mecha_v1"]

# A figure facing the camera, arms straight down, in a square photo.
# Its left side is on the right of the photo.
STANDING = {
    "nose": (0.50, 0.10), "left_eye": (0.52, 0.09), "right_eye": (0.48, 0.09), "left_ear": (0.54, 0.10), "right_ear": (0.46, 0.10),
    "left_shoulder": (0.60, 0.25), "right_shoulder": (0.40, 0.25), "left_elbow": (0.62, 0.40), "right_elbow": (0.38, 0.40),
    "left_wrist": (0.62, 0.55), "right_wrist": (0.38, 0.55), "left_hip": (0.56, 0.55), "right_hip": (0.44, 0.55),
    "left_knee": (0.56, 0.75), "right_knee": (0.44, 0.75), "left_ankle": (0.56, 0.95), "right_ankle": (0.44, 0.95),
}


def coco(points: dict, score: float = 0.9, overrides: dict[str, float] | None = None) -> list[RawPoint]:
    overrides = overrides or {}
    return [RawPoint(*points[n], overrides.get(n, score)) for n in COCO17]


def test_maps_every_humanoid_keypoint_and_derives_the_spine():
    kps = map_to_profile(coco(STANDING), HUMANOID)

    assert list(kps) == HUMANOID.keypoints
    assert kps["left_elbow"].x == pytest.approx(0.62) and kps["left_elbow"].source == "direct"
    assert (kps["neck"].x, kps["neck"].y) == pytest.approx((0.50, 0.25))
    assert kps["neck"].source == "derived"
    # chest and waist sit between the neck and the hip centre (0.50, 0.55)
    assert kps["chest"].y == pytest.approx(0.25 + 0.30 * 0.30)
    assert kps["waist"].y == pytest.approx(0.25 + 0.80 * 0.30)
    assert kps["head"].y == pytest.approx(0.096, abs=0.01)


def test_low_scores_become_uncertain_or_hidden_without_coordinates():
    kps = map_to_profile(coco(STANDING, overrides={"left_wrist": 0.4, "right_ankle": 0.1}), HUMANOID)

    assert kps["left_wrist"].visibility == "uncertain"
    assert kps["right_ankle"].visibility == "not_visible"
    assert kps["right_ankle"].x is None


def test_spine_is_not_derived_when_hips_are_hidden():
    kps = map_to_profile(coco(STANDING, overrides={"left_hip": 0.05, "right_hip": 0.05}), HUMANOID)

    assert kps["neck"].visibility == "visible"
    assert kps["chest"].x is None and kps["waist"].x is None


def test_mecha_only_landmarks_are_marked_not_estimated():
    kps = map_to_profile(coco(STANDING), MECHA)

    for name in ("backpack", "left_shoulder_armor", "right_shoulder_armor"):
        assert kps[name].visibility == "not_estimated"
    assert kps["left_knee"].visibility == "visible"


def test_rejects_wrong_number_of_points():
    with pytest.raises(ValueError):
        map_to_profile([RawPoint(0, 0, 1)] * 5, HUMANOID)


@pytest.mark.parametrize("a, b, c, expected", [
    ((0, 0), (1, 0), (2, 0), 180),
    ((0, 0), (1, 0), (1, 1), 90),
    ((1, 0), (0, 0), (1, 1), 45),
])
def test_interior_angle(a, b, c, expected):
    assert interior_angle(a, b, c) == pytest.approx(expected)


def test_interior_angle_uses_real_proportions():
    # In a 2:1 landscape photo, equal normalized steps are twice as wide as tall.
    assert interior_angle((0, 0), (0.5, 0), (0.5, 0.5), aspect=2.0) == pytest.approx(90)
    assert interior_angle((0, 0), (0.5, 0.5), (1.0, 0), aspect=1.0) == pytest.approx(90)
    assert interior_angle((0, 0), (0.5, 0.5), (1.0, 0), aspect=2.0) != pytest.approx(90)


def test_build_pose_measures_straight_and_bent_joints():
    bent = dict(STANDING, right_wrist=(0.50, 0.40))  # right forearm folded across
    pose = build_pose(coco(bent), HUMANOID, (1000, 1000))

    assert pose.joint_angles["left_elbow"] == pytest.approx(172.4, abs=0.5)
    # upper arm (0.02, -0.15) vs forearm (0.12, 0): acos(0.132) = 82.4 degrees
    assert pose.joint_angles["right_elbow"] == pytest.approx(82.4, abs=0.5)
    assert pose.joint_angles["left_knee"] == pytest.approx(180)
    assert pose.orientation == "front"
    assert pose.visible_count == 16 and pose.hidden == []


def test_build_pose_reports_hidden_joints_and_skips_their_angles():
    pose = build_pose(coco(STANDING, overrides={"left_wrist": 0.2}), HUMANOID, (1000, 1000))

    assert "left_wrist" in pose.hidden
    assert "left_elbow" not in pose.joint_angles
    assert pose.visible_count == 15


def test_orientation_back_and_side():
    no_face = {n: 0.05 for n in ("nose", "left_eye", "right_eye", "left_ear", "right_ear")}
    assert build_pose(coco(STANDING, overrides=no_face), HUMANOID, (1000, 1000)).orientation == "back"

    side = dict(STANDING, left_shoulder=(0.51, 0.25), right_shoulder=(0.49, 0.25))
    assert build_pose(coco(side), HUMANOID, (1000, 1000)).orientation == "side"


def test_embedding_ignores_position_and_size():
    small_and_moved = {n: (0.2 + x * 0.5, 0.1 + y * 0.5) for n, (x, y) in STANDING.items()}
    a = embedding(map_to_profile(coco(STANDING), HUMANOID), HUMANOID, 1.0)
    b = embedding(map_to_profile(coco(small_and_moved), HUMANOID), HUMANOID, 1.0)

    assert len(a) == 3 * len(HUMANOID.keypoints)
    assert a == pytest.approx(b, abs=1e-3)


def test_embedding_is_zero_without_a_torso():
    hidden = {n: 0.0 for n in COCO17}
    assert set(embedding(map_to_profile(coco(STANDING, overrides=hidden), HUMANOID), HUMANOID, 1.0)) == {0.0}
