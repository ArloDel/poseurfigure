from app.services.pose_extractor import COCO17, RawPoint, map_to_profile
from app.services.pose_matcher import PoseView, mirror
from app.services.pose_sketch import LEFT, RIGHT, draw_skeleton
from tests.conftest import PROFILES
from tests.fakes import STANDING

H = PROFILES["humanoid_v1"]


def view(points: dict, hidden: tuple = (), aspect: float = 0.75) -> PoseView:
    kps = map_to_profile([RawPoint(*points[n], 0.05 if n in hidden else 0.9) for n in COCO17], H)
    return PoseView(kps, aspect)


def color_near(img, x: float, y: float) -> set:
    w, h = img.size
    return {img.getpixel((min(w - 1, max(0, round(x * w) + dx)), min(h - 1, max(0, round(y * h) + dy))))
            for dx in range(-3, 4) for dy in range(-3, 4)}


def test_keeps_the_target_aspect_and_colors_each_side():
    v = view(STANDING)
    img = draw_skeleton(v, H, height=800)
    assert img.size == (600, 800)
    lk, rk = v.keypoints["left_knee"], v.keypoints["right_knee"]
    assert LEFT in color_near(img, lk.x, lk.y)
    assert RIGHT in color_near(img, rk.x, rk.y)


def test_mirrored_target_swaps_sides_in_the_picture():
    v = mirror(view(STANDING))
    img = draw_skeleton(v, H, height=800)
    # After mirroring, the figure's left knee is where the right knee was, and still drawn blue.
    lk = v.keypoints["left_knee"]
    assert LEFT in color_near(img, lk.x, lk.y)
    assert abs(lk.x - (1 - view(STANDING).keypoints["right_knee"].x)) < 1e-9


def test_hidden_joints_are_left_out():
    img = draw_skeleton(view(STANDING, hidden=("left_ankle",)), H, height=800)
    a = view(STANDING).keypoints["left_ankle"]
    assert color_near(img, a.x, a.y) == {(255, 255, 255)}
