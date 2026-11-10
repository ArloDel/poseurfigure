from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageFilter

from app.main import app, get_pipeline

client = TestClient(app)


def jpeg(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def detailed(w=900, h=1200, level=128) -> Image.Image:
    """A sharp, textured test image (checkerboard plus noise) at a given mean brightness."""
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:h, 0:w]
    board = ((xx // 24 + yy // 24) % 2) * 80 - 40
    arr = np.clip(level + board + rng.normal(0, 12, (h, w)), 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")


def test_health_lists_profiles():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert {"humanoid_v1", "anime_v1", "mecha_v1"} <= set(body["profiles"])


def test_profiles_endpoint():
    res = client.get("/v1/profiles")
    assert res.status_code == 200
    mecha = next(p for p in res.json() if p["profile"] == "mecha_v1")
    assert "backpack" in mecha["keypoints"]


def test_sharp_photo_runs_the_pipeline():
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(detailed()), "image/jpeg")},
                      headers={"X-Request-Id": "abc"})
    assert res.status_code == 200
    assert res.headers["X-Request-Id"] == "abc"
    body = res.json()
    assert body["quality"]["ok"] is True
    assert body["stage"] == "keypoints"
    assert body["profile"] == "humanoid_v1"
    assert body["classification"]["source"] == "model"
    assert body["pose"]["visible_count"] == 16
    assert len(body["pose"]["embedding"]) == 48
    assert body["pose"]["keypoints"]["left_elbow"]["visibility"] == "visible"


def test_user_profile_and_figure_choice_are_passed_through():
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(detailed()), "image/jpeg")},
                      data={"profile": "mecha_v1", "figure_index": "0"})
    body = res.json()
    assert body["profile"] == "mecha_v1"
    assert body["classification"]["source"] == "user"
    assert body["selected_figure"] == 0


def test_photo_without_a_figure_explains_why(fake_models):
    fake_models.detections = []
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(detailed()), "image/jpeg")})
    body = res.json()
    assert body["quality"]["ok"] is False
    assert body["quality"]["issues"][-1]["code"] == "no_figure"


def test_rejected_photo_never_reaches_the_models(fake_models):
    blurry = detailed().filter(ImageFilter.GaussianBlur(12))
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(blurry), "image/jpeg")})
    assert res.json()["stage"] == "quality_only"
    assert fake_models.calls == 0


def test_models_can_be_switched_off():
    app.dependency_overrides[get_pipeline] = lambda: None
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(detailed()), "image/jpeg")})
    body = res.json()
    assert body["stage"] == "quality_only"
    assert body["model_version"] == "quality-check-0.1"


@pytest.mark.parametrize("img,code", [
    (detailed().filter(ImageFilter.GaussianBlur(12)), "blurry"),
    (detailed(level=15), "too_dark"),
    (detailed(w=300, h=300), "too_small"),
])
def test_unsuitable_photos_explain_why(img, code):
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(img), "image/jpeg")})
    assert res.status_code == 200
    quality = res.json()["quality"]
    assert quality["ok"] is False
    assert code in [i["code"] for i in quality["issues"]]


def test_unreadable_file_is_rejected():
    res = client.post("/v1/analyze", files={"image": ("f.jpg", b"not an image", "image/jpeg")})
    assert res.status_code == 422


def test_unknown_profile_is_rejected():
    res = client.post("/v1/analyze", files={"image": ("f.jpg", jpeg(detailed()), "image/jpeg")},
                      data={"profile": "dragon_v9"})
    assert res.status_code == 422
