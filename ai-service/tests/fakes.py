"""Fake models so tests never download or run the real ones."""
from app.models.object_detector import Detection
from app.services.pose_extractor import COCO17, RawPoint

STANDING = {
    "nose": (0.50, 0.10), "left_eye": (0.52, 0.09), "right_eye": (0.48, 0.09), "left_ear": (0.54, 0.10), "right_ear": (0.46, 0.10),
    "left_shoulder": (0.60, 0.25), "right_shoulder": (0.40, 0.25), "left_elbow": (0.62, 0.40), "right_elbow": (0.38, 0.40),
    "left_wrist": (0.62, 0.55), "right_wrist": (0.38, 0.55), "left_hip": (0.56, 0.55), "right_hip": (0.44, 0.55),
    "left_knee": (0.56, 0.75), "right_knee": (0.44, 0.75), "left_ankle": (0.56, 0.95), "right_ankle": (0.44, 0.95),
}


class FakeDetector:
    version = "fake-det"

    def __init__(self, detections=None):
        self.detections = [Detection((0.3, 0.05, 0.7, 0.98), 0.9, "q")] if detections is None else detections
        self.calls = 0

    def detect(self, image):
        self.calls += 1
        return list(self.detections)


class FakeClassifier:
    version = "fake-cls"

    def __init__(self, scores=None):
        self.scores = scores or {"humanoid_v1": 0.8, "anime_v1": 0.15, "mecha_v1": 0.05}
        self.calls = 0

    def classify(self, crop):
        self.calls += 1
        return dict(self.scores)


class FakeEstimator:
    version = "fake-pose"

    def __init__(self, scores: dict[str, float] | None = None):
        self.scores = scores or {}
        self.boxes = []

    def estimate(self, image, bbox):
        self.boxes.append(bbox)
        return [RawPoint(*STANDING[n], self.scores.get(n, 0.9)) for n in COCO17]
