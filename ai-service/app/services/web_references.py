"""Pose ideas from Pinterest, for a personally run instance only (AI_PINTEREST_ENABLED, off by default).

Pinterest's terms don't allow automated collection, and the photos belong to the people who posted them. This
exists because the app's owner runs it for themselves; never enable it on a server other people use. Found
images are kept privately as pose references and are not shown to anyone else.

search(): the same request pinterest.com's own search page makes (the approach follows pinscrape, MIT), with
a pause between requests. It returns image URLs only: no pin link or author.
read(): downloads one image (Pinterest's image CDN only, size-capped) and reads it with the same models as user
photos. Only full-body, readable poses are kept: close-ups, figures held in a hand and photos without a figure
are rejected with a reason, so they aren't fetched again.
"""
from __future__ import annotations

import io
import json
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote, quote_plus, urlparse

import httpx
from PIL import Image

from app.services.image_quality import UnreadableImage, load_image
from app.services.pipeline import Pipeline
from app.services.pose_extractor import build_pose
from app.schemas.analysis import FigureDetection, SkeletonProfile

BASE_URL = "https://in.pinterest.com"
IMAGE_HOSTS = {"i.pinimg.com"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_SIDE = 900
# Same rule as the catalog (catalog/build.py): the torso anchors and enough joints must be visible.
ANCHORS = ("neck", "left_hip", "right_hip")
MIN_VISIBLE = 10
# A figure box this small is a background figure or a detail shot, not the subject.
MIN_BOX_AREA = 0.12
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/139.0.0.0 Safari/537.36")


class SearchFailed(Exception):
    pass


class PinterestSearch:
    """One search at a time, with a pause between requests, so a personal instance stays a light user."""

    def __init__(self, pause: float = 2.0, client: httpx.Client | None = None):
        self.pause = pause
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=True)
        self._lock = threading.Lock()
        self._last = 0.0

    def _wait(self):
        delay = self.pause - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def _headers(self, source_url: str) -> dict:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/javascript, */*, q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "X-Pinterest-Appstate": "active",
            "X-Pinterest-Pws-Handler": "www/search/[scope].js",
            "X-Pinterest-Source-Url": source_url,
            "Referer": f"{BASE_URL}/",
        }

    def search(self, query: str, limit: int = 25) -> list[str]:
        source_url = f"/search/pins/?q={quote(query)}&rs=typed"
        options = {"query": query, "scope": "pins", "rs": "typed", "page_size": str(limit), "redux_normalize_feed": True,
                   "source_url": source_url, "auto_correction_disabled": False}
        params = {"source_url": source_url, "data": json.dumps({"options": options, "context": {}}, separators=(",", ":")),
                  "_": str(int(time.time() * 1000))}
        with self._lock:
            try:
                self._wait()
                # The search page first, like a browser: it sets the cookies the resource call needs.
                self._client.get(f"{BASE_URL}{source_url}", headers={"User-Agent": USER_AGENT})
                self._wait()
                res = self._client.get(f"{BASE_URL}/resource/BaseSearchResource/get/", params=params,
                                       headers=self._headers(source_url))
            except httpx.HTTPError as exc:
                raise SearchFailed(f"Pinterest request failed: {type(exc).__name__}") from exc
        if res.status_code != 200:
            raise SearchFailed(f"Pinterest answered {res.status_code}")
        try:
            results = res.json()["resource_response"]["data"]["results"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SearchFailed("Pinterest's answer had an unexpected shape") from exc
        urls = []
        for r in results or []:
            orig = ((r or {}).get("images") or {}).get("orig") or {}
            url = orig.get("url")
            if url and allowed_image_url(url) and url not in urls:
                urls.append(url)
        return urls[:limit]


def allowed_image_url(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and u.hostname in IMAGE_HOSTS


@dataclass
class ReadResult:
    accepted: bool
    reason: str | None
    data: dict


def download(url: str, client: httpx.Client) -> Image.Image:
    if not allowed_image_url(url):
        raise UnreadableImage("Only Pinterest's image server is allowed.")
    with client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as res:
        if res.status_code != 200:
            raise UnreadableImage(f"Image download failed ({res.status_code}).")
        body = b""
        for chunk in res.iter_bytes():
            body += chunk
            if len(body) > MAX_IMAGE_BYTES:
                raise UnreadableImage("Image is too large.")
    return load_image(body)


def read(image: Image.Image, profile: SkeletonProfile, pipeline: Pipeline) -> ReadResult:
    """Reads one reference photo. Keypoints are normalized to the (resized) image returned in `data`."""
    im = image.copy()
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    dets = pipeline.detector.detect(im)
    if not dets:
        return ReadResult(False, "no_figure", {})
    figs = [FigureDetection(bbox=list(d.bbox), score=d.score) for d in dets]
    x0, y0, x1, y1 = figs[pipeline.pick(figs)].bbox
    if (x1 - x0) * (y1 - y0) < MIN_BOX_AREA:
        return ReadResult(False, "figure_too_small", {})
    pose = build_pose(pipeline.estimator.estimate(im, (x0, y0, x1, y1)), profile, im.size)
    missing = [a for a in ANCHORS if pose.keypoints[a].visibility != "visible"]
    if missing or pose.visible_count < MIN_VISIBLE:
        return ReadResult(False, "pose_incomplete", {"visible_count": pose.visible_count})
    crop = im.crop((x0 * im.width, y0 * im.height, x1 * im.width, y1 * im.height))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return ReadResult(True, None, {
        "image_jpeg": buf.getvalue(), "width": im.width, "height": im.height,
        "figure_box": [round(v, 4) for v in (x0, y0, x1, y1)],
        "keypoints": {n: {"x": k.x, "y": k.y, "visibility": k.visibility} for n, k in pose.keypoints.items()},
        "joint_angles": pose.joint_angles, "orientation": pose.orientation, "visible_count": pose.visible_count,
        "appearance": pipeline.classifier.embed(crop), "appearance_version": pipeline.classifier.version,
    })
