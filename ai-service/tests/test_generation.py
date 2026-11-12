import base64
import json
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, get_generator, get_pipeline
from app.models.object_detector import Detection
from app.services.image_generator import StubGenerator, build_generator, build_prompt
from app.services.pipeline import Pipeline
from app.services.pose_extractor import COCO17, RawPoint, map_to_profile
from tests.conftest import PROFILES
from tests.fakes import STANDING, FakeClassifier, FakeDetector, FakeEstimator

client = TestClient(app)
H = PROFILES["humanoid_v1"]
CROUCH = dict(STANDING, left_knee=(0.62, 0.65), right_knee=(0.38, 0.65), left_ankle=(0.56, 0.78), right_ankle=(0.44, 0.78))
ARM_UP = dict(STANDING, right_elbow=(0.40, 0.10), right_wrist=(0.40, 0.0))


def photo() -> bytes:
    arr = (np.random.default_rng(0).random((800, 800, 3)) * 255).astype("uint8")
    buf = BytesIO()
    Image.fromarray(arr).save(buf, "JPEG")
    return buf.getvalue()


def payload(points: dict, **extra) -> str:
    kps = map_to_profile([RawPoint(*points[n], 0.9) for n in COCO17], H)
    return json.dumps({"profile": "humanoid_v1", "instructions": [{"body_part": "left_knee", "movement": "bend", "target_angle": 90}],
                       "target": {"keypoints": {n: {"x": k.x, "y": k.y, "visibility": k.visibility} for n, k in kps.items()},
                                  "image_size": [800, 800]}, **extra})


class EchoGenerator:
    """Returns a square image; the fake pose model then 'finds' the STANDING pose in it."""
    name = "echo"

    def generate(self, source, prompt, target, profile):
        self.prompt = prompt
        return Image.new("RGB", (800, 800), "white")


@pytest.fixture
def generator():
    gen = EchoGenerator()
    app.dependency_overrides[get_generator] = lambda: gen
    return gen


def post(points, **extra):
    return client.post("/v1/generate", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"payload": payload(points, **extra)})


def test_generated_image_matching_the_target_is_validated(generator):
    res = post(STANDING)
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "echo"
    assert body["validation"]["status"] == "validated"
    assert body["validation"]["similarity"] > 0.99
    img = Image.open(BytesIO(base64.b64decode(body["image_base64"])))
    assert img.size == (body["width"], body["height"]) == (800, 800)
    assert "left knee bent (about 90 degrees)" in generator.prompt


def test_image_showing_another_pose_is_rejected(generator):
    body = post(CROUCH).json()
    assert body["validation"]["status"] == "rejected"
    assert body["validation"]["reason"] == "pose_mismatch"
    # The average similarity alone would pass (~0.89): the knees give it away.
    assert body["validation"]["similarity"] > 0.85
    assert body["validation"]["worst_joint"].endswith("knee") and body["validation"]["worst_joint_error"] > 40


def test_image_without_a_figure_is_rejected(generator):
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(FakeDetector([]), FakeClassifier(), FakeEstimator(), PROFILES)
    assert post(STANDING).json()["validation"] == {"status": "rejected", "reason": "no_figure", "similarity": None}


def test_unreadable_pose_in_the_image_is_rejected(generator):
    hidden = {n: 0.05 for n in ("left_hip", "right_hip")}
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(
        FakeDetector([Detection((0.1, 0.1, 0.9, 0.9), 0.9, "q")]), FakeClassifier(), FakeEstimator(hidden), PROFILES)
    assert post(STANDING).json()["validation"]["reason"] == "pose_unreadable"


def test_mirrored_request_targets_the_mirror_image(generator):
    left_arm_up = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(
        FakeDetector(), FakeClassifier(), _Fixed(left_arm_up), PROFILES)
    body = post(ARM_UP, mirrored=True).json()
    assert body["validation"]["status"] == "validated"
    assert "right knee bent" in generator.prompt  # instructions are mirrored too


def test_without_models_the_image_stays_unvalidated(generator):
    app.dependency_overrides[get_pipeline] = lambda: None
    assert post(STANDING).json()["validation"]["status"] == "unvalidated"


def test_feature_is_off_without_a_provider():
    app.dependency_overrides[get_generator] = lambda: None
    assert post(STANDING).status_code == 503


def test_bad_payload_and_unknown_profile_are_rejected(generator):
    files = {"image": ("f.jpg", photo(), "image/jpeg")}
    assert client.post("/v1/generate", files=files, data={"payload": "{not json"}).status_code == 422
    bad = json.loads(payload(STANDING)) | {"profile": "dragon_v9"}
    assert client.post("/v1/generate", files=files, data={"payload": json.dumps(bad)}).status_code == 422


def test_stub_keeps_the_photo_and_adds_a_banner():
    src = Image.new("RGB", (1000, 500), "red")
    out = StubGenerator().generate(src, "p", None, H)
    assert out.width == 768 and out.height == 384 + 34
    assert out.getpixel((10, 10)) == (255, 0, 0)


def test_build_generator_and_prompt():
    assert build_generator("none") is None
    assert build_generator("stub").name == "stub"
    with pytest.raises(ValueError):
        build_generator("magic")
    prompt = build_prompt(H, [], mirrored=False)
    assert "Keep its identity" in prompt and "reference skeleton" in prompt


class _Fixed(FakeEstimator):
    def __init__(self, points):
        super().__init__()
        self.points = points

    def estimate(self, image, bbox):
        return [RawPoint(*self.points[n], 0.9) for n in COCO17]
