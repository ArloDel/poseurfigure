"""Pinterest references against fake HTTP: nothing here contacts Pinterest."""
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.main import app, get_pinterest, get_pipeline
from app.models.object_detector import Detection
from app.services import web_references as wr
from app.services.pipeline import Pipeline
from tests.conftest import PROFILES
from tests.fakes import FakeClassifier, FakeDetector, FakeEstimator
from tests.test_generation import client

H = PROFILES["humanoid_v1"]


def search_body(*urls) -> dict:
    return {"resource_response": {"data": {"results": [{"images": {"orig": {"url": u}}} for u in urls] + [{"images": None}]}}}


class Fake:
    def __init__(self, status=200, body=None, image=None):
        self.status, self.body, self.image, self.requests = status, body, image, []

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        if request.url.host == "i.pinimg.com":
            return httpx.Response(200, content=self.image or b"")
        if "/resource/" in request.url.path:
            return httpx.Response(self.status, json=self.body)
        return httpx.Response(200, text="<html></html>")


def searcher(fake) -> wr.PinterestSearch:
    return wr.PinterestSearch(pause=0, client=httpx.Client(transport=httpx.MockTransport(fake)))


def test_search_returns_pinterest_image_urls_only_once_each():
    fake = Fake(body=search_body("https://i.pinimg.com/originals/a.jpg", "https://evil.example/x.jpg",
                                 "https://i.pinimg.com/originals/a.jpg", "http://i.pinimg.com/originals/b.jpg",
                                 "https://i.pinimg.com/originals/c.png"))
    urls = searcher(fake).search("Spider-Man figure", limit=10)
    assert urls == ["https://i.pinimg.com/originals/a.jpg", "https://i.pinimg.com/originals/c.png"]
    api = fake.requests[-1]
    assert api.url.path == "/resource/BaseSearchResource/get/" and "Spider-Man" in api.url.params["data"]
    assert fake.requests[0].url.path == "/search/pins/"  # the search page first, like a browser


@pytest.mark.parametrize("status,body", [(403, {}), (200, {"unexpected": True})])
def test_search_failures_are_reported(status, body):
    with pytest.raises(wr.SearchFailed):
        searcher(Fake(status, body)).search("x")


def jpeg(size=(600, 900)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, "gray").save(buf, "JPEG")
    return buf.getvalue()


def test_download_only_from_pinterest_and_capped(monkeypatch):
    c = httpx.Client(transport=httpx.MockTransport(Fake(image=jpeg())))
    assert wr.download("https://i.pinimg.com/originals/a.jpg", c).size == (600, 900)
    with pytest.raises(wr.UnreadableImage):
        wr.download("https://example.com/a.jpg", c)
    monkeypatch.setattr(wr, "MAX_IMAGE_BYTES", 100)
    with pytest.raises(wr.UnreadableImage):
        wr.download("https://i.pinimg.com/originals/a.jpg", c)


def pipe(dets=None, hidden=None) -> Pipeline:
    return Pipeline(FakeDetector(dets), FakeClassifier(), FakeEstimator(hidden), PROFILES)


def test_a_full_body_pose_is_accepted_with_keypoints_look_and_a_smaller_image():
    r = wr.read(Image.new("RGB", (1800, 2400), "white"), H, pipe())
    assert r.accepted and r.reason is None
    assert (r.data["width"], r.data["height"]) == (675, 900)
    assert r.data["visible_count"] >= 10 and r.data["keypoints"]["neck"]["visibility"] == "visible"
    assert len(r.data["appearance"]) == 3 and r.data["image_jpeg"][:2] == b"\xff\xd8"


@pytest.mark.parametrize("dets,hidden,reason", [
    ([], None, "no_figure"),
    ([Detection((0.4, 0.4, 0.55, 0.6), 0.9, "q")], None, "figure_too_small"),
    (None, {"left_hip": 0.05, "right_hip": 0.05}, "pose_incomplete"),  # a close-up: no hips
])
def test_unusable_photos_are_rejected_with_a_reason(dets, hidden, reason):
    r = wr.read(Image.new("RGB", (800, 1000), "white"), H, pipe(dets, hidden))
    assert not r.accepted and r.reason == reason


def test_endpoints_are_off_unless_enabled():
    app.dependency_overrides[get_pinterest] = lambda: None
    assert client.post("/v1/references/search", json={"query": "x"}).status_code == 503
    assert client.post("/v1/references/read", json={"url": "https://i.pinimg.com/a.jpg", "profile": "humanoid_v1"}).status_code == 503


def test_search_and_read_endpoints(monkeypatch):
    fake = Fake(body=search_body("https://i.pinimg.com/originals/a.jpg"), image=jpeg())
    app.dependency_overrides[get_pinterest] = lambda: searcher(fake)
    res = client.post("/v1/references/search", json={"query": "Spider-Man figure", "limit": 5})
    assert res.status_code == 200 and res.json()["urls"] == ["https://i.pinimg.com/originals/a.jpg"]
    assert client.post("/v1/references/search", json={"query": ""}).status_code == 422

    monkeypatch.setattr("app.main._download_client", lambda: httpx.Client(transport=httpx.MockTransport(fake)))
    body = client.post("/v1/references/read", json={"url": "https://i.pinimg.com/originals/a.jpg", "profile": "humanoid_v1"}).json()
    assert body["accepted"] is True and body["image_base64"] and body["figure_box"]
    bad = client.post("/v1/references/read", json={"url": "https://example.com/a.jpg", "profile": "humanoid_v1"}).json()
    assert bad == {"accepted": False, "reason": "unreadable", "detail": "Only Pinterest's image server is allowed."}
    assert client.post("/v1/references/read", json={"url": "https://i.pinimg.com/a.jpg", "profile": "dragon"}).status_code == 422

    app.dependency_overrides[get_pipeline] = lambda: None
    assert client.post("/v1/references/read", json={"url": "https://i.pinimg.com/a.jpg", "profile": "humanoid_v1"}).status_code == 503
