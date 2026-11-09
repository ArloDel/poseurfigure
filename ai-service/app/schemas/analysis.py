from typing import Literal

from pydantic import BaseModel


class QualityIssue(BaseModel):
    code: Literal["too_small", "blurry", "too_dark", "too_bright", "unreadable"]
    message: str


class QualityReport(BaseModel):
    ok: bool
    width: int
    height: int
    sharpness: float
    brightness: float
    issues: list[QualityIssue]


class AnalyzeResponse(BaseModel):
    model_version: str
    # Pipeline stage reached. Sprint 1 stops after quality checks; detection/keypoints come in Sprint 4.
    stage: Literal["quality_only", "detected", "keypoints"]
    profile: str | None
    quality: QualityReport
    pose: dict | None = None


class SkeletonProfile(BaseModel):
    profile: str
    name: str
    category: str
    version: int
    keypoints: list[str]
    connections: list[list[str]]
