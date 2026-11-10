import asyncio
import threading
import time
from io import BytesIO

import httpx
from PIL import Image

from app.main import app, get_pipeline
from tests.conftest import PROFILES
from tests.fakes import FakeClassifier, FakeDetector, FakeEstimator
from app.services.pipeline import Pipeline


class SlowDetector(FakeDetector):
    """Records how many detections run at the same time."""

    def __init__(self):
        super().__init__()
        self.active = self.peak = 0
        self._lock = threading.Lock()

    def detect(self, image):
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.2)
        with self._lock:
            self.active -= 1
        return super().detect(image)


def _photo() -> bytes:
    import numpy as np

    rng = np.random.default_rng(0)
    arr = (rng.random((900, 700, 3)) * 255).astype("uint8")
    buf = BytesIO()
    Image.fromarray(arr).save(buf, "JPEG")
    return buf.getvalue()


def test_inference_runs_one_request_at_a_time():
    det = SlowDetector()
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(det, FakeClassifier(), FakeEstimator(), PROFILES)
    photo = _photo()

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await asyncio.gather(*[
                client.post("/v1/analyze", files={"image": ("f.jpg", photo, "image/jpeg")}) for _ in range(3)
            ])

    responses = asyncio.run(run())

    assert [r.status_code for r in responses] == [200, 200, 200]
    assert all(r.json()["stage"] == "keypoints" for r in responses)
    assert det.calls == 3
    assert det.peak == 1
