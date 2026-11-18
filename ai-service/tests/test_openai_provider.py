"""OpenAI provider against a fake HTTP transport: nothing here calls OpenAI or costs anything."""
import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.config import Settings
from app.main import app, get_generator, get_pipeline
from app.services.image_generator import GenerationFailed, OpenAIGenerator, build_generator
from app.services.pipeline import Pipeline
from tests.conftest import PROFILES
from tests.fakes import STANDING, FakeClassifier, FakeDetector
from tests.test_generation import ARM_UP, _Fixed, client, payload, photo
from tests.test_pose_sketch import view

H = PROFILES["humanoid_v1"]


def png(color="white", size=(64, 96)) -> str:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class Recorder:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.requests = status, body, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = self.body if self.body is not None else {"data": [{"b64_json": png("navy")}]}
        return httpx.Response(self.status, json=body)


def provider(rec: Recorder) -> OpenAIGenerator:
    return OpenAIGenerator("sk-test", "gpt-image-1-mini", "low", "1024x1536",
                           client=httpx.Client(transport=httpx.MockTransport(rec)))


def test_sends_photo_reference_and_stick_figure_and_returns_the_image():
    rec = Recorder()
    out = provider(rec).generate(Image.new("RGB", (800, 800), "red"), "Target pose: left knee bent.", view(STANDING),
                                 H, reference=Image.new("RGB", (600, 900), "green"))
    assert out.size == (64, 96) and out.getpixel((0, 0)) == (0, 0, 128)
    req = rec.requests[0]
    assert req.url == "https://api.openai.com/v1/images/edits"
    assert req.headers["Authorization"] == "Bearer sk-test"
    body = req.content.decode("latin-1")
    assert body.count('name="image[]"') == 3
    assert 'name="model"\r\n\r\ngpt-image-1-mini' in body and 'name="quality"\r\n\r\nlow' in body
    assert "Image 3 is a stick figure" in body and "Target pose: left knee bent." in body


def test_without_a_reference_photo_two_images_are_sent():
    rec = Recorder()
    provider(rec).generate(Image.new("RGB", (800, 800)), "p", view(STANDING), H)
    body = rec.requests[0].content.decode("latin-1")
    assert body.count('name="image[]"') == 2 and "Image 2 is a stick figure" in body


@pytest.mark.parametrize("status,retryable", [(429, True), (500, True), (400, False), (401, False)])
def test_errors_say_whether_a_retry_can_help(status, retryable):
    rec = Recorder(status, {"error": {"code": "moderation_blocked" if status == 400 else "x"}})
    with pytest.raises(GenerationFailed) as exc:
        provider(rec).generate(Image.new("RGB", (800, 800)), "p", view(STANDING), H)
    assert exc.value.retryable is retryable and str(status) in str(exc.value)


def test_a_reply_without_an_image_is_a_failure():
    with pytest.raises(GenerationFailed):
        provider(Recorder(200, {"data": []})).generate(Image.new("RGB", (800, 800)), "p", view(STANDING), H)


def test_build_needs_a_key():
    with pytest.raises(ValueError):
        build_generator("openai", Settings(openai_api_key=""))
    assert build_generator("openai", Settings(openai_api_key="sk-x")).name == "openai"


class _Failing:
    name = "failing"

    def __init__(self, retryable):
        self.retryable = retryable

    def generate(self, *a, **kw):
        raise GenerationFailed("provider down", retryable=self.retryable)


@pytest.mark.parametrize("retryable,code", [(True, 502), (False, 422)])
def test_endpoint_reports_provider_failures(retryable, code):
    app.dependency_overrides[get_generator] = lambda: _Failing(retryable)
    res = client.post("/v1/generate", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"payload": payload(STANDING)})
    assert res.status_code == code


class _Capture:
    name = "capture"

    def generate(self, source, prompt, target, profile, reference=None):
        self.reference = reference
        return Image.new("RGB", (800, 800), "white")


def test_reference_photo_reaches_the_provider_and_is_flipped_for_a_mirrored_request():
    gen = _Capture()
    app.dependency_overrides[get_generator] = lambda: gen
    ref = Image.new("RGB", (100, 50), "white")
    ref.paste((255, 0, 0), (0, 0, 10, 50))  # red stripe on the left
    buf = BytesIO()
    ref.save(buf, "PNG")
    files = {"image": ("f.jpg", photo(), "image/jpeg"), "reference": ("r.png", buf.getvalue(), "image/png")}
    client.post("/v1/generate", files=files, data={"payload": payload(STANDING)})
    assert gen.reference.getpixel((2, 25))[0] > 200
    client.post("/v1/generate", files=files, data={"payload": payload(STANDING, mirrored=True)})
    assert gen.reference.getpixel((97, 25))[0] > 200 and gen.reference.getpixel((2, 25))[1] > 200


def test_a_result_that_only_matches_when_flipped_is_validated_as_mirrored():
    # The provider drew the target (right arm up) as its mirror image (left arm up).
    left_arm_up = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))
    app.dependency_overrides[get_generator] = lambda: _Capture()
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(FakeDetector(), FakeClassifier(), _Fixed(left_arm_up), PROFILES)
    res = client.post("/v1/generate", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"payload": payload(ARM_UP)})
    v = res.json()["validation"]
    assert v["status"] == "validated" and v["mirrored"] is True


def test_a_straight_match_is_not_marked_mirrored():
    app.dependency_overrides[get_generator] = lambda: _Capture()
    res = client.post("/v1/generate", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"payload": payload(STANDING)})
    v = res.json()["validation"]
    assert v["status"] == "validated" and v["mirrored"] is False
