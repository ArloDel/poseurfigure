"""Keypoints with ViTPose (top-down: runs on the detected figure box). POSE-01..03.

ViTPose is trained on people (COCO-17). On figures it is a baseline to measure, not a final model:
the PRD expects a figure-specific keypoint model once a training dataset exists.
"""
from __future__ import annotations

import threading
from typing import Protocol

from PIL import Image

from app.models.registry import POSE
from app.services.pose_extractor import RawPoint


class PoseEstimator(Protocol):
    version: str

    def estimate(self, image: Image.Image, bbox: tuple[float, float, float, float]) -> list[RawPoint]:
        """COCO-17 keypoints in COCO order, normalized to the full image."""
        ...


class VitPoseEstimator:
    version = POSE.tag

    def __init__(self, box_padding: float = 0.1, cache_dir: str | None = None):
        self.box_padding = box_padding
        self._cache_dir = cache_dir
        self._lock = threading.Lock()
        self._model = self._processor = None

    def _load(self):
        with self._lock:
            if self._model is None:
                from transformers import AutoProcessor, VitPoseForPoseEstimation

                self._processor = AutoProcessor.from_pretrained(POSE.repo, revision=POSE.revision, cache_dir=self._cache_dir)
                self._model = VitPoseForPoseEstimation.from_pretrained(POSE.repo, revision=POSE.revision, cache_dir=self._cache_dir).eval()

    def estimate(self, image: Image.Image, bbox: tuple[float, float, float, float]) -> list[RawPoint]:
        import torch

        self._load()
        w, h = image.size
        x0, y0, x1, y1 = bbox
        # A little margin so hands and feet at the box edge aren't cut off.
        pw, ph = (x1 - x0) * self.box_padding, (y1 - y0) * self.box_padding
        x0, y0, x1, y1 = max(0, x0 - pw), max(0, y0 - ph), min(1, x1 + pw), min(1, y1 + ph)
        coco_box = [[x0 * w, y0 * h, (x1 - x0) * w, (y1 - y0) * h]]  # COCO format: x, y, width, height in pixels

        inputs = self._processor(image, boxes=[coco_box], return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs)
        person = self._processor.post_process_pose_estimation(outputs, boxes=[coco_box])[0][0]
        return [RawPoint(float(x) / w, float(y) / h, float(s))
                for (x, y), s in zip(person["keypoints"].tolist(), person["scores"].tolist())]
