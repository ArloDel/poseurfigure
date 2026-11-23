"""Pose ideas for a figure (the product's core idea): show the same character in other poses first, then figures
that look like it, and favor poses that differ from how the figure stands now.

The user photographs a figure as it is, often its default standing pose. What helps is not a pose close to that
one but pictures of that character, or of figures like it, posed in ways worth copying.

For every candidate:
  - same_character: its character name matches the one the user confirmed (variants ignored: "Spider-Man
    (symbiote suit)" matches "Spider-Man").
  - look: cosine similarity of the two figures' SigLIP 2 image embeddings. Figures of the same character, or
    with the same kind of suit and build, score high.
  - novelty: 1 when the candidate's pose is far from the figure's current pose, 0 when it is the same pose.
    The larger of two signals: overall pose similarity, and the biggest single joint change (an average hides
    one big move: a crouch scores ~0.9 against standing, yet the knees bend ~55 degrees). Neutral without a pose.
  - feasibility: how well the pose fits the figure's joint limits, as in recommender.py.
score = 0.6 x look + 0.25 x novelty + 0.15 x feasibility. Same-character picks come first, then the rest; within
each group picks are made one at a time so each next pose also differs from the poses already picked.

Weights and thresholds are starting values to tune with real photos.
"""
from __future__ import annotations

import math

from app.schemas.analysis import InspireRequest, Recommendation, RecommendResponse, SkeletonProfile
from app.services.figure_identifier import same_character
from app.services.pose_changes import changes
from app.services.pose_extractor import joint_angles
from app.services.pose_matcher import feasibility, match, to_view
from app.services.recommender import _basis

INSPIRATION_VERSION = "inspire-0.1"
W_LOOK, W_NOVELTY, W_FEAS = 0.6, 0.25, 0.15
SIMILAR_LOOK = 0.7  # cosine above which a figure counts as "looks like yours"
SAME_POSE, NEW_POSE = 0.95, 0.75  # pose similarity: at or above SAME_POSE nothing new, at or below NEW_POSE all new
BIG_MOVE = 60.0  # degrees: one joint moving this much makes the pose fully new
MMR_LAMBDA = 0.75
DUPLICATE = 0.95


def cosine(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b or len(a) != len(b):
        return None
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else None


def inspire(request: InspireRequest, profile: SkeletonProfile) -> RecommendResponse:
    query = to_view(request.pose.keypoints, request.pose.image_size) if request.pose else None
    basis = _basis(query) if query is not None else "type_only"
    limits = {j: lim.model_dump() for j, lim in request.figure_limits.items()}
    excluded = set(request.exclude_ids)

    rows = []
    for c in request.candidates:
        if c.id in excluded:
            continue
        view = to_view(c.keypoints, c.image_size)
        m = match(query, view, profile) if basis == "pose" else None
        if not view.angles:
            view.angles = joint_angles(view.keypoints, profile, view.aspect)
        f = feasibility(view.angles, profile, limits)
        look = cosine(request.appearance, c.appearance)
        steps = changes(query, view, m.mirrored) if m is not None else []
        if m is None:
            novelty = 0.5
        else:
            by_similarity = (SAME_POSE - m.similarity) / (SAME_POSE - NEW_POSE)
            biggest = max((abs(s["delta"]) for s in steps if s.get("delta") is not None), default=0.0)
            novelty = min(1.0, max(0.0, by_similarity, biggest / BIG_MOVE))
        same = same_character(request.character, c.character)
        score = W_LOOK * (look if look is not None else 0.5) + W_NOVELTY * novelty + W_FEAS * f.score
        rows.append({"c": c, "view": view, "m": m, "f": f, "look": look, "novelty": novelty, "same": same, "score": score,
                     "steps": steps})

    k = max(0, request.top_k)
    same_rows = _pick([r for r in rows if r["same"]], profile, k)
    rest = _pick([r for r in rows if not r["same"]], profile, k - len(same_rows))

    results = []
    for r in same_rows + rest:
        c, m, f, look = r["c"], r["m"], r["f"], r["look"]
        similar = look is not None and look >= SIMILAR_LOOK
        group = "same_character" if r["same"] else "similar_look" if similar else "more"
        reasons = ["same_character"] if r["same"] else ["similar_look"] if similar else []
        if m is not None and r["novelty"] >= 0.5:
            reasons.append("new_pose")
        if f.warnings:
            reasons.append("check_joints")
        sim = m.similarity if m is not None else 0.5
        results.append(Recommendation(
            id=c.id, score=round(r["score"], 4), similarity=round(sim, 4), feasibility=f.score,
            components=m.components if m is not None else {}, shared_joints=m.shared_joints if m is not None else 0,
            mirrored=bool(m and m.mirrored), warnings=f.warnings, reasons=reasons,
            changes=r["steps"],
            group=group, look=round(look, 4) if look is not None else None,
        ))
    return RecommendResponse(matcher_version=INSPIRATION_VERSION, profile=profile.profile, basis=basis, results=results,
                             remaining=max(0, len(rows) - len(results)))


def _pick(rows: list[dict], profile: SkeletonProfile, k: int) -> list[dict]:
    """Best score first, then each next pick must also differ in pose from those already chosen."""
    pair: dict[tuple[int, int], float] = {}

    def alike(a, b) -> float:
        key = (min(a["c"].id, b["c"].id), max(a["c"].id, b["c"].id))
        if key not in pair:
            pair[key] = match(a["view"], b["view"], profile).similarity
        return pair[key]

    chosen: list[dict] = []
    left = list(rows)
    while left and len(chosen) < k:
        def value(r):
            if not chosen:
                return r["score"]
            redundancy = max(alike(r, s) for s in chosen)
            return MMR_LAMBDA * r["score"] - (1 - MMR_LAMBDA) * redundancy - (1.0 if redundancy >= DUPLICATE else 0.0)
        best = max(left, key=lambda r: (round(value(r), 6), -r["c"].id))
        chosen.append(best)
        left.remove(best)
    return chosen
