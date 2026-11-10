"""Analysis pipeline (PRD 8.1 steps 2-5): detect figures, pick one, classify its profile, estimate keypoints."""
from __future__ import annotations

import math
import time

from PIL import Image

from app.models.figure_classifier import FigureClassifier
from app.models.object_detector import FigureDetector
from app.models.pose_estimator import PoseEstimator
from app.schemas.analysis import (
    AnalyzeResponse, Classification, FigureDetection, QualityIssue, QualityReport, SkeletonProfile,
)
from app.services.pose_extractor import Thresholds, build_pose

PIPELINE_VERSION = "pipeline-0.2"

NO_FIGURE = QualityIssue(
    code="no_figure",
    message="We couldn't find a figure in this photo. Fit the whole figure in the frame, in focus, against a plain background.",
)


class Pipeline:
    def __init__(self, detector: FigureDetector, classifier: FigureClassifier, estimator: PoseEstimator,
                 profiles: dict[str, SkeletonProfile], min_profile_confidence: float = 0.6,
                 thresholds: Thresholds = Thresholds()):
        self.detector, self.classifier, self.estimator = detector, classifier, estimator
        self.profiles = profiles
        self.min_profile_confidence = min_profile_confidence
        self.thresholds = thresholds

    @property
    def version(self) -> str:
        return f"{PIPELINE_VERSION}+{self.detector.version}+{self.classifier.version}+{self.estimator.version}"

    @property
    def models(self) -> dict[str, str]:
        return {"detector": self.detector.version, "classifier": self.classifier.version, "pose": self.estimator.version}

    @staticmethod
    def pick(figures: list[FigureDetection]) -> int:
        """The main subject: confident and large. score x sqrt(area) keeps a big, slightly less certain figure
        ahead of a small confident one in the background."""
        def weight(f: FigureDetection) -> float:
            x0, y0, x1, y1 = f.bbox
            return f.score * math.sqrt(max(0.0, (x1 - x0) * (y1 - y0)))
        return max(range(len(figures)), key=lambda i: weight(figures[i]))

    def run(self, image: Image.Image, quality: QualityReport, profile: str | None = None,
            figure_index: int | None = None) -> AnalyzeResponse:
        timings: dict[str, int] = {}

        def timed(key, fn, *args):
            t = time.perf_counter()
            out = fn(*args)
            timings[key] = round((time.perf_counter() - t) * 1000)
            return out

        dets = timed("detect", self.detector.detect, image)
        figures = [FigureDetection(bbox=[round(v, 4) for v in d.bbox], score=round(d.score, 4)) for d in dets]
        base = dict(model_version=self.version, models=self.models, profile=profile, figures=figures, timings_ms=timings)

        if not figures:
            # IMG-07: a readable photo with nothing to analyze is a clear, final answer.
            failed = quality.model_copy(update={"ok": False, "issues": [*quality.issues, NO_FIGURE]})
            return AnalyzeResponse(stage="detected", quality=failed, **base)

        # FIG-04: the app may name a figure; otherwise pick the main one.
        index = figure_index if figure_index is not None and 0 <= figure_index < len(figures) else self.pick(figures)
        x0, y0, x1, y1 = figures[index].bbox
        w, h = image.size

        if profile is not None:
            classification = Classification(profile=profile, confidence=1.0, scores={}, needs_confirmation=False, source="user")
        else:
            crop = image.crop((x0 * w, y0 * h, x1 * w, y1 * h))
            scores = timed("classify", self.classifier.classify, crop)
            best = max(scores, key=scores.get)
            classification = Classification(profile=best, confidence=scores[best], scores=scores,
                                            needs_confirmation=scores[best] < self.min_profile_confidence)

        raw = timed("pose", self.estimator.estimate, image, (x0, y0, x1, y1))
        pose = build_pose(raw, self.profiles[classification.profile], image.size, self.thresholds)

        return AnalyzeResponse(stage="keypoints", quality=quality, selected_figure=index,
                               classification=classification, pose=pose, **{**base, "profile": classification.profile})
