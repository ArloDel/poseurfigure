from typing import Literal

from pydantic import BaseModel


class QualityIssue(BaseModel):
    code: Literal["too_small", "blurry", "too_dark", "too_bright", "unreadable", "no_figure"]
    message: str


class QualityReport(BaseModel):
    ok: bool
    width: int
    height: int
    sharpness: float
    brightness: float
    issues: list[QualityIssue]


Visibility = Literal["visible", "uncertain", "not_visible", "not_estimated"]


class Keypoint(BaseModel):
    """Normalized 0-1 image coordinates. x/y are null when the joint couldn't be located."""
    x: float | None
    y: float | None
    confidence: float
    visibility: Visibility
    # "direct" comes straight from the model; "derived" is computed from other joints (neck, chest, waist).
    source: Literal["direct", "derived", "none"] = "direct"


class FigureDetection(BaseModel):
    bbox: list[float]  # [x0, y0, x1, y1], normalized
    score: float


class Classification(BaseModel):
    profile: str
    confidence: float
    scores: dict[str, float]
    # Low confidence: the app asks the user to confirm or pick the figure type (FIG-03).
    needs_confirmation: bool
    source: Literal["model", "user"] = "model"


class PoseResult(BaseModel):
    profile: str
    keypoints: dict[str, Keypoint]
    # Interior angle in degrees, 2D image plane, 180 = straight. Only where all three joints are visible.
    joint_angles: dict[str, float]
    orientation: Literal["front", "back", "side", "unknown"]
    embedding: list[float]
    embedding_version: str
    visible_count: int
    hidden: list[str]


class AnalyzeResponse(BaseModel):
    model_version: str
    # Pipeline stage reached: quality_only (photo rejected or models off), detected (no keypoints), keypoints.
    stage: Literal["quality_only", "detected", "keypoints"]
    profile: str | None
    quality: QualityReport
    figures: list[FigureDetection] = []
    selected_figure: int | None = None
    classification: Classification | None = None
    pose: PoseResult | None = None
    models: dict[str, str] = {}
    timings_ms: dict[str, int] = {}


class PosePoint(BaseModel):
    x: float | None
    y: float | None
    visibility: Visibility = "visible"
    confidence: float = 1.0


class PoseInput(BaseModel):
    keypoints: dict[str, PosePoint]
    image_size: tuple[int, int]  # width, height of the photo the coordinates are normalized to


class Candidate(PoseInput):
    id: int
    category: str | None = None
    difficulty: str | None = None


class JointLimit(BaseModel):
    min: float
    max: float


class RecommendRequest(BaseModel):
    profile: str
    pose: PoseInput
    candidates: list[Candidate]
    # Known limits of the user's own figure (PRD 8.5). Overrides the profile's estimates.
    figure_limits: dict[str, JointLimit] = {}
    top_k: int = 5


class Recommendation(BaseModel):
    id: int
    score: float
    similarity: float
    feasibility: float
    components: dict[str, float]
    shared_joints: int
    mirrored: bool
    warnings: list[dict]


class RecommendResponse(BaseModel):
    matcher_version: str
    profile: str
    results: list[Recommendation]


class SkeletonProfile(BaseModel):
    profile: str
    name: str
    category: str
    version: int
    keypoints: list[str]
    connections: list[list[str]]
    joints: dict[str, dict] = {}
