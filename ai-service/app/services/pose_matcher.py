"""Pose matching and feasibility (PRD 8.4, 8.5).

similarity  S = 0.40 * S_angle + 0.35 * S_position + 0.25 * S_embedding
  - S_angle: joint angles both poses have, 1 - |difference| / 180, averaged.
  - S_position: keypoints both poses show, centered on the hips and scaled by torso length,
    Gaussian of the distance (sigma 0.35 torso lengths), averaged.
  - S_embedding: cosine similarity of the geo-v1 embeddings on shared dimensions, mapped to 0..1.
  A missing component (no shared angles, say) drops out and the remaining weights are renormalized.
  Poses sharing few joints are shrunk toward 0.5, since two visible arms say little about a whole pose.

Each candidate is also compared with the user's pose mirrored (left and right swapped): a mirrored
pose is just as easy to copy, and the app can say "mirror it".

feasibility F: how well the target's joint angles fit the limits of the user's figure (the figure's own
known limits when given, else the profile's estimated ones). 1 = all within range.

Weights are illustrative starting values from the PRD and must be tuned on labeled data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.schemas.analysis import Keypoint, SkeletonProfile
from app.services.pose_extractor import embedding as geo_embedding
from app.services.pose_extractor import joint_angles

W_ANGLE, W_POSITION, W_EMBEDDING = 0.40, 0.35, 0.25
POSITION_SIGMA = 0.35  # torso lengths
FULL_COVERAGE = 10  # shared joints for full confidence in the similarity
FEASIBILITY_SOFTNESS = 30.0  # degrees past a limit for the joint to count as impossible


@dataclass
class PoseView:
    """What matching needs from a pose: keypoints (normalized to its own photo) and that photo's aspect."""
    keypoints: dict[str, Keypoint]
    aspect: float
    angles: dict[str, float] = field(default_factory=dict)


@dataclass
class Match:
    similarity: float
    components: dict[str, float]
    shared_joints: int
    mirrored: bool


@dataclass
class Feasibility:
    score: float
    warnings: list[dict]


def _normalized(view: PoseView) -> dict[str, tuple[float, float]]:
    """Visible keypoints relative to the hip centre, in torso lengths (aspect-corrected)."""
    k = view.keypoints

    def p(n):
        j = k.get(n)
        return (j.x * view.aspect, j.y) if j is not None and j.visibility == "visible" and j.x is not None else None

    lh, rh, neck = p("left_hip"), p("right_hip"), p("neck")
    if not (lh and rh and neck):
        return {}
    cx, cy = (lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2
    scale = math.dist((cx, cy), neck)
    if scale < 1e-6:
        return {}
    return {n: ((q[0] - cx) / scale, (q[1] - cy) / scale) for n in k if (q := p(n))}


def _swap(name: str) -> str:
    if name.startswith("left_"):
        return "right_" + name[5:]
    if name.startswith("right_"):
        return "left_" + name[6:]
    return name


def mirror(view: PoseView) -> PoseView:
    """The same pose seen in a mirror: x flipped, left and right swapped."""
    kps = {}
    for n, j in view.keypoints.items():
        kps[_swap(n)] = j.model_copy(update={"x": None if j.x is None else 1.0 - j.x})
    return PoseView(kps, view.aspect, {_swap(n): a for n, a in view.angles.items()})


def _cosine(a: list[float], b: list[float]) -> float | None:
    # Use only dimensions where both poses have the keypoint (every 3rd value is the presence flag).
    va, vb = [], []
    for i in range(0, min(len(a), len(b)), 3):
        if a[i + 2] and b[i + 2]:
            va += a[i:i + 2]
            vb += b[i:i + 2]
    na, nb = math.hypot(*va) if va else 0, math.hypot(*vb) if vb else 0
    if na < 1e-9 or nb < 1e-9:
        return None
    return sum(x * y for x, y in zip(va, vb)) / (na * nb)


def _similarity(query: PoseView, cand: PoseView, profile: SkeletonProfile) -> tuple[float, dict[str, float], int]:
    comps: dict[str, float] = {}

    shared_angles = [j for j in query.angles if j in cand.angles]
    if shared_angles:
        comps["angle"] = sum(1 - abs(query.angles[j] - cand.angles[j]) / 180 for j in shared_angles) / len(shared_angles)

    qn, cn = _normalized(query), _normalized(cand)
    shared = [n for n in qn if n in cn]
    if shared:
        comps["position"] = sum(math.exp(-math.dist(qn[n], cn[n]) ** 2 / (2 * POSITION_SIGMA ** 2)) for n in shared) / len(shared)

    cos = _cosine(geo_embedding(query.keypoints, profile, query.aspect), geo_embedding(cand.keypoints, profile, cand.aspect))
    if cos is not None:
        comps["embedding"] = (cos + 1) / 2

    weights = {"angle": W_ANGLE, "position": W_POSITION, "embedding": W_EMBEDDING}
    total = sum(weights[c] for c in comps)
    if not total:
        return 0.0, comps, 0
    s = sum(weights[c] * v for c, v in comps.items()) / total
    coverage = min(1.0, len(shared) / FULL_COVERAGE)
    s = 0.5 + (s - 0.5) * coverage  # little shared evidence -> stay near "don't know"
    return s, comps, len(shared)


def match(query: PoseView, cand: PoseView, profile: SkeletonProfile) -> Match:
    for v in (query, cand):
        if not v.angles:
            v.angles = joint_angles(v.keypoints, profile, v.aspect)
    straight = _similarity(query, cand, profile)
    mirrored = _similarity(mirror(query), cand, profile)
    best, is_mirror = (mirrored, True) if mirrored[0] > straight[0] + 0.01 else (straight, False)
    s, comps, shared = best
    return Match(round(s, 4), {k: round(v, 4) for k, v in comps.items()}, shared, is_mirror)


MATCHER_VERSION = "match-0.1"
# Sprint 5 ranking: mostly "how close is this to what your figure already does", with room for poses
# your figure can actually hold. Sprint 6 adds diversity so the list isn't five versions of one pose.
RANK_SIMILARITY, RANK_FEASIBILITY = 0.7, 0.3


def to_view(points: dict, image_size: tuple[int, int]) -> PoseView:
    kps = {n: Keypoint(x=p.x, y=p.y, confidence=p.confidence, visibility=p.visibility) for n, p in points.items()}
    return PoseView(kps, image_size[0] / image_size[1])


def recommend(request, profile: SkeletonProfile):
    from app.schemas.analysis import Recommendation, RecommendResponse

    query = to_view(request.pose.keypoints, request.pose.image_size)
    limits = {j: lim.model_dump() for j, lim in request.figure_limits.items()}
    results = []
    for c in request.candidates:
        cand = to_view(c.keypoints, c.image_size)
        m = match(query, cand, profile)
        f = feasibility(cand.angles, profile, limits)
        results.append(Recommendation(
            id=c.id, score=round(RANK_SIMILARITY * m.similarity + RANK_FEASIBILITY * f.score, 4),
            similarity=m.similarity, feasibility=f.score, components=m.components,
            shared_joints=m.shared_joints, mirrored=m.mirrored, warnings=f.warnings,
        ))
    results.sort(key=lambda r: r.score, reverse=True)
    return RecommendResponse(matcher_version=MATCHER_VERSION, profile=profile.profile, results=results[: max(0, request.top_k)])


def feasibility(target_angles: dict[str, float], profile: SkeletonProfile,
                figure_limits: dict[str, dict] | None = None) -> Feasibility:
    """How well a target pose fits the figure's joint ranges. Figure limits override the profile's."""
    limits = {j: {**cfg, "source": cfg.get("source", "estimated")} for j, cfg in profile.joints.items()}
    for j, lim in (figure_limits or {}).items():
        limits[j] = {**limits.get(j, {}), **lim, "source": "figure"}

    penalties, warnings = [], []
    for joint, a in target_angles.items():
        lim = limits.get(joint)
        if not lim or "min" not in lim or "max" not in lim:
            continue
        past = max(lim["min"] - a, a - lim["max"], 0.0)
        penalties.append(min(1.0, past / FEASIBILITY_SOFTNESS))
        if past > 0:
            warnings.append({"joint": joint, "target": round(a), "limit": lim["min"] if a < lim["min"] else lim["max"],
                             "beyond_by": round(past), "limit_source": lim["source"]})
    score = 1.0 - (sum(penalties) / len(penalties) if penalties else 0.0)
    # One impossible joint makes the whole pose impossible to hold, whatever the average says.
    if penalties:
        score = min(score, 1.0 - 0.6 * max(penalties))
    return Feasibility(round(score, 4), warnings)
