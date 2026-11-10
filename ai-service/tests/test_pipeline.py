from pathlib import Path

from PIL import Image

from app.models.object_detector import Detection, contained, iou, nms, relative_filter
from app.schemas.analysis import FigureDetection, QualityReport
from app.services.pipeline import Pipeline
from app.services.profiles import load_profiles
from tests.fakes import FakeClassifier, FakeDetector, FakeEstimator

PROFILES = load_profiles(Path(__file__).resolve().parents[2] / "shared" / "skeleton_profiles")
IMAGE = Image.new("RGB", (800, 1000), "white")
QUALITY = QualityReport(ok=True, width=800, height=1000, sharpness=200, brightness=128, issues=[])


def pipeline(**kw) -> Pipeline:
    return Pipeline(kw.get("det", FakeDetector()), kw.get("cls", FakeClassifier()), kw.get("est", FakeEstimator()), PROFILES)


def test_full_run_returns_profile_keypoints_and_versions():
    result = pipeline().run(IMAGE, QUALITY)

    assert result.stage == "keypoints"
    assert result.profile == "humanoid_v1"
    assert result.classification.needs_confirmation is False
    assert result.pose.visible_count == 16
    assert set(result.timings_ms) == {"detect", "classify", "pose"}
    assert "fake-det" in result.model_version and result.models["pose"] == "fake-pose"


def test_no_figure_fails_the_quality_check_with_a_reason():
    result = pipeline(det=FakeDetector([])).run(IMAGE, QUALITY)

    assert result.quality.ok is False
    assert result.quality.issues[-1].code == "no_figure"
    assert result.pose is None and result.classification is None


def test_uncertain_type_asks_the_user_to_confirm():
    cls = FakeClassifier({"humanoid_v1": 0.45, "anime_v1": 0.40, "mecha_v1": 0.15})
    result = pipeline(cls=cls).run(IMAGE, QUALITY)

    assert result.classification.profile == "humanoid_v1"
    assert result.classification.needs_confirmation is True


def test_user_chosen_profile_skips_the_classifier():
    cls = FakeClassifier()
    result = pipeline(cls=cls).run(IMAGE, QUALITY, profile="mecha_v1")

    assert cls.calls == 0
    assert result.classification.source == "user"
    assert result.pose.profile == "mecha_v1"
    assert result.pose.keypoints["backpack"].visibility == "not_estimated"


def test_picks_the_big_figure_over_a_small_confident_one():
    small = Detection((0.05, 0.05, 0.15, 0.2), 0.95, "q")
    big = Detection((0.3, 0.1, 0.9, 0.95), 0.6, "q")
    est = FakeEstimator()
    result = pipeline(det=FakeDetector([small, big]), est=est).run(IMAGE, QUALITY)

    assert result.selected_figure == 1
    assert est.boxes[0] == tuple(result.figures[1].bbox)


def test_app_can_choose_the_figure():
    dets = [Detection((0.3, 0.1, 0.9, 0.95), 0.9, "q"), Detection((0.0, 0.0, 0.2, 0.3), 0.5, "q")]
    result = pipeline(det=FakeDetector(dets)).run(IMAGE, QUALITY, figure_index=1)
    assert result.selected_figure == 1

    out_of_range = pipeline(det=FakeDetector(dets)).run(IMAGE, QUALITY, figure_index=7)
    assert out_of_range.selected_figure == 0


def test_pick_weighs_score_by_size():
    figs = [FigureDetection(bbox=[0, 0, 0.1, 0.1], score=0.99), FigureDetection(bbox=[0, 0, 0.8, 0.8], score=0.5)]
    assert Pipeline.pick(figs) == 1


def test_nms_drops_parts_inside_a_stronger_figure():
    figure = Detection((0.1, 0.1, 0.9, 0.95), 0.73, "q")
    torso = Detection((0.27, 0.16, 0.77, 0.51), 0.36, "q")  # OWLv2 also fires on the upper body
    other = Detection((0.0, 0.5, 0.15, 0.9), 0.6, "q")
    assert [d.score for d in nms([figure, torso, other], 0.5)] == [0.73, 0.6]


def test_relative_filter_drops_weak_detections_next_to_a_strong_one():
    dets = [Detection((0, 0, 1, 1), 0.65, "q"), Detection((0, 0, 1, 1), 0.53, "q"), Detection((0, 0, 1, 1), 0.3, "q")]
    assert [d.score for d in relative_filter(dets, 0.6)] == [0.65, 0.53]
    assert relative_filter([], 0.6) == []


def test_contained():
    assert contained((0.2, 0.2, 0.4, 0.4), (0, 0, 1, 1)) == 1.0
    assert contained((0.5, 0.5, 1.5, 1.5), (0, 0, 1, 1)) == 0.25


def test_iou_and_nms():
    a, b, c = (0, 0, 1, 1), (0, 0, 1, 0.5), (2, 2, 3, 3)
    assert iou(a, b) == 0.5 and iou(a, c) == 0
    kept = nms([Detection(a, 0.9, "q"), Detection((0, 0, 0.95, 1), 0.8, "q"), Detection(c, 0.7, "q")], 0.5)
    assert [d.score for d in kept] == [0.9, 0.7]
