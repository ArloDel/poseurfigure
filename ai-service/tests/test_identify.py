"""Character recognition against a fake HTTP transport: nothing here calls OpenAI."""
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.config import Settings
from app.main import app, get_identifier
from app.services.figure_identifier import (
    IdentifyFailed, OpenAIIdentifier, build_identifier, character_key, normalize,
)
from tests.test_generation import client, photo


def answer(**fields) -> dict:
    data = {"character": "Spider-Man", "variant": "symbiote suit", "franchise": "Marvel", "figure_line": "MAFEX",
            "confidence": "high"} | fields
    return {"choices": [{"message": {"content": json.dumps(data), "refusal": None}}]}


class Recorder:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.requests = status, body, []

    def __call__(self, request):
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body if self.body is not None else answer())


def identifier(rec) -> OpenAIIdentifier:
    return OpenAIIdentifier("sk-test", "gpt-5.4-mini", client=httpx.Client(transport=httpx.MockTransport(rec)))


def test_names_the_character_and_sends_a_small_image_with_a_strict_schema():
    rec = Recorder()
    out = identifier(rec).identify(Image.new("RGB", (2000, 3000), "black"))
    assert out["display_name"] == "Spider-Man (symbiote suit)"
    assert out["key"] == "spiderman" and out["franchise"] == "Marvel" and out["confidence"] == "high"
    body = json.loads(rec.requests[0].content)
    assert body["model"] == "gpt-5.4-mini"  # as configured by the test
    assert body["response_format"]["json_schema"]["strict"] is True
    url = body["messages"][0]["content"][1]["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,") and len(url) < 200_000  # resized, not the full photo


def test_unknown_character_is_low_confidence():
    out = identifier(Recorder(body=answer(character="", variant="", confidence="medium"))).identify(Image.new("RGB", (50, 50)))
    assert out["character"] == "" and out["display_name"] == "" and out["confidence"] == "low"


@pytest.mark.parametrize("status,retryable", [(429, True), (503, True), (400, False), (401, False)])
def test_errors_say_whether_a_retry_helps(status, retryable):
    with pytest.raises(IdentifyFailed) as exc:
        identifier(Recorder(status, {"error": {"code": "x"}})).identify(Image.new("RGB", (50, 50)))
    assert exc.value.retryable is retryable


def test_a_refusal_is_not_retried():
    body = {"choices": [{"message": {"content": None, "refusal": "I can't help with that."}}]}
    with pytest.raises(IdentifyFailed) as exc:
        identifier(Recorder(body=body)).identify(Image.new("RGB", (50, 50)))
    assert exc.value.retryable is False


def test_character_key_ignores_case_punctuation_and_variant():
    assert character_key("Spider-Man (Symbiote Suit)") == character_key("spiderman") == "spiderman"
    assert character_key("Iron Man Mark 85") != character_key("Iron Man")
    assert character_key(None) == "" and normalize({}, "m")["confidence"] == "low"
    assert normalize({"character": "Spider-Man", "figure_line": "Unknown"}, "m")["figure_line"] == ""


def test_build_identifier():
    assert build_identifier("none") is None
    with pytest.raises(ValueError):
        build_identifier("openai", Settings(openai_api_key=""))
    with pytest.raises(ValueError):
        build_identifier("magic", Settings())


class _Capture:
    name = "capture"

    def __init__(self, fail=None):
        self.fail, self.crop = fail, None

    def identify(self, crop):
        if self.fail:
            raise self.fail
        self.crop = crop
        return normalize({"character": "Spider-Man", "variant": "", "franchise": "Marvel", "figure_line": "",
                          "confidence": "medium"}, "m")


def test_endpoint_crops_to_the_figure_box_with_a_margin():
    cap = _Capture()
    app.dependency_overrides[get_identifier] = lambda: cap
    res = client.post("/v1/identify", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"bbox": "[0.25, 0.25, 0.75, 0.75]"})
    assert res.status_code == 200
    assert res.json()["display_name"] == "Spider-Man" and res.json()["provider"] == "capture"
    assert cap.crop.size == (440, 440)  # 800 px photo: box 400 px + 5% margin on each side


@pytest.mark.parametrize("bbox", ["[0.5, 0.5, 0.2, 0.9]", "nope", "[1, 2]"])
def test_endpoint_rejects_a_bad_box(bbox):
    app.dependency_overrides[get_identifier] = lambda: _Capture()
    res = client.post("/v1/identify", files={"image": ("f.jpg", photo(), "image/jpeg")}, data={"bbox": bbox})
    assert res.status_code == 422


def test_endpoint_is_off_without_a_provider_and_reports_failures():
    app.dependency_overrides[get_identifier] = lambda: None
    files = {"image": ("f.jpg", photo(), "image/jpeg")}
    assert client.post("/v1/identify", files=files).status_code == 503
    app.dependency_overrides[get_identifier] = lambda: _Capture(IdentifyFailed("down"))
    assert client.post("/v1/identify", files=files).status_code == 502
    app.dependency_overrides[get_identifier] = lambda: _Capture(IdentifyFailed("declined", retryable=False))
    assert client.post("/v1/identify", files=files).status_code == 422
