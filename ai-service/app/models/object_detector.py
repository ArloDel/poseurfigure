"""Figure detection with OWLv2 (open-vocabulary, zero-shot). FIG-01, IMG-07, IMG-08."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from PIL import Image

from app.models.registry import DETECTOR


@dataclass(frozen=True)
class Detection:
    bbox: tuple[float, float, float, float]  # normalized x0, y0, x1, y1
    score: float
    query: str


class FigureDetector(Protocol):
    version: str

    def detect(self, image: Image.Image) -> list[Detection]: ...


# Text queries describe what we look for; the best-matching query's score is kept per box.
QUERIES = [
    "a photo of an action figure",
    "a photo of a toy figure",
    "a photo of a plastic robot model kit",
    "a photo of an anime figurine",
]


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def contained(inner, outer) -> float:
    """Share of `inner`'s area that lies inside `outer`."""
    ix = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    iy = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    area = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return ix * iy / area if area > 0 else 0.0


def nms(dets: list[Detection], iou_threshold: float, containment: float = 0.85) -> list[Detection]:
    """Standard NMS, plus: drop a box that mostly sits inside a stronger one
    (OWLv2 also fires on a figure's head or torso as if it were a separate figure)."""
    kept: list[Detection] = []
    for d in sorted(dets, key=lambda d: d.score, reverse=True):
        if all(iou(d.bbox, k.bbox) < iou_threshold and contained(d.bbox, k.bbox) < containment for k in kept):
            kept.append(d)
    return kept


def relative_filter(dets: list[Detection], ratio: float) -> list[Detection]:
    """Keep detections scoring at least `ratio` x the best one: loose accessories and props
    around a figure score well below the figure itself."""
    if not dets:
        return dets
    top = max(d.score for d in dets)
    return [d for d in dets if d.score >= ratio * top]


class Owlv2Detector:
    version = DETECTOR.tag

    def __init__(self, threshold: float = 0.2, iou_threshold: float = 0.5, max_figures: int = 8,
                 relative_threshold: float = 0.6, cache_dir: str | None = None):
        self.threshold, self.iou_threshold, self.max_figures = threshold, iou_threshold, max_figures
        self.relative_threshold = relative_threshold
        self._cache_dir = cache_dir
        self._lock = threading.Lock()
        self._model = self._processor = None

    def _load(self):
        with self._lock:
            if self._model is None:
                from transformers import Owlv2ForObjectDetection, Owlv2Processor

                self._processor = Owlv2Processor.from_pretrained(DETECTOR.repo, revision=DETECTOR.revision, cache_dir=self._cache_dir)
                self._model = Owlv2ForObjectDetection.from_pretrained(DETECTOR.repo, revision=DETECTOR.revision, cache_dir=self._cache_dir).eval()

    def detect(self, image: Image.Image) -> list[Detection]:
        import torch

        self._load()
        inputs = self._processor(text=[QUERIES], images=image, return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs)
        # OWLv2 pads the image to a square, so boxes are relative to the padded side.
        side = max(image.size)
        result = self._processor.post_process_grounded_object_detection(
            outputs, threshold=self.threshold, target_sizes=[(side, side)], text_labels=[QUERIES]
        )[0]
        w, h = image.size
        dets = []
        for box, score, label in zip(result["boxes"].tolist(), result["scores"].tolist(), result["text_labels"]):
            x0, y0, x1, y1 = box
            nb = (max(0.0, x0 / w), max(0.0, y0 / h), min(1.0, x1 / w), min(1.0, y1 / h))
            if nb[2] - nb[0] > 0.01 and nb[3] - nb[1] > 0.01:
                dets.append(Detection(nb, float(score), label))
        return relative_filter(nms(dets, self.iou_threshold), self.relative_threshold)[: self.max_figures]
