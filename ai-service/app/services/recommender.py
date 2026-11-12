"""Hybrid recommendation ranking (PRD 4.5, 8.4): turns match and feasibility scores into a short, varied list.

v1 ("score"): sort by 0.7 x similarity + 0.3 x feasibility. Sprint 5 showed two problems with it:
  - many poses score within a few hundredths of each other, so small keypoint errors reorder the list;
  - nothing stops five near-identical poses from filling the list.
v2 ("hybrid"):
  - similarity is rounded down into bands, so differences smaller than the noise don't decide the order;
    ties break on feasibility, then easier difficulty, then catalog order, never on raw similarity;
  - picks are made one at a time (maximal marginal relevance): each next pose must score well AND differ
    from the poses already picked, with an extra nudge toward categories not shown yet;
  - when the user's pose can't be read (no torso, too few joints), it doesn't pretend: basis becomes
    "type_only" and the list is just varied, feasible poses for the figure type.
"""
from __future__ import annotations

import math

from app.schemas.analysis import Recommendation, RecommendRequest, RecommendResponse, SkeletonProfile
from app.services.pose_matcher import _normalized, feasibility, match, to_view

MATCHER_VERSION = "match-0.2"
W_SIM, W_FEAS = 0.7, 0.3
BAND = 0.05  # similarity differences below this are treated as noise
MMR_LAMBDA = 0.75  # 1 = pure score, 0 = pure variety
CATEGORY_NUDGE = 0.04  # extra cost for repeating a category already in the list
# Two catalog poses this alike are the same pose to the user: the second goes to the back of the line.
# (MMR alone isn't enough: a near-copy can outscore a genuinely different pose by more than the
# redundancy penalty takes away.)
DUPLICATE = 0.95
MIN_QUERY_JOINTS = 8  # visible joints needed to compare poses at all
CLOSE, FAR = 0.85, 0.75  # similarity thresholds for the "close" and "new direction" reasons
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _basis(query) -> str:
    joints = _normalized(query)
    return "pose" if joints and len(joints) >= MIN_QUERY_JOINTS else "type_only"


def _reasons(sim: float, mirrored: bool, warnings: list, new_category: bool, basis: str) -> list[str]:
    r = []
    if basis == "pose":
        # Every pick ranked against the user's pose says how far it is: close, a few changes, or new.
        if sim >= CLOSE:
            r.append("close_to_current")
        elif sim >= FAR:
            r.append("few_changes")
        else:
            r.append("new_direction")
        if mirrored:
            r.append("mirror")
    if new_category:
        r.append("different_category")
    if warnings:
        r.append("check_joints")
    return r


def rank(request: RecommendRequest, profile: SkeletonProfile, strategy: str = "hybrid") -> RecommendResponse:
    query = to_view(request.pose.keypoints, request.pose.image_size)
    limits = {j: lim.model_dump() for j, lim in request.figure_limits.items()}
    excluded = set(request.exclude_ids)
    pool = [c for c in request.candidates if c.id not in excluded]
    basis = _basis(query) if strategy == "hybrid" else "pose"

    rows = []
    for c in pool:
        view = to_view(c.keypoints, c.image_size)
        m = match(query, view, profile)
        f = feasibility(view.angles, profile, limits)
        rows.append({"c": c, "view": view, "m": m, "f": f})

    if strategy == "score":
        rows.sort(key=lambda r: W_SIM * r["m"].similarity + W_FEAS * r["f"].score, reverse=True)
        picked = rows[: max(0, request.top_k)]
    else:
        picked = _mmr(rows, profile, basis, max(0, request.top_k))

    results, seen_categories = [], set()
    for r in picked:
        c, m, f = r["c"], r["m"], r["f"]
        new_cat = bool(c.category) and c.category not in seen_categories and bool(seen_categories)
        seen_categories.add(c.category)
        sim = m.similarity if basis == "pose" else 0.5
        results.append(Recommendation(
            id=c.id, score=round(W_SIM * sim + W_FEAS * f.score, 4), similarity=round(sim, 4), feasibility=f.score,
            components=m.components if basis == "pose" else {}, shared_joints=m.shared_joints,
            mirrored=m.mirrored and basis == "pose", warnings=f.warnings,
            reasons=_reasons(sim, m.mirrored, f.warnings, new_cat, basis),
        ))
    return RecommendResponse(matcher_version=MATCHER_VERSION if strategy == "hybrid" else "match-0.1",
                             profile=profile.profile, basis=basis, results=results,
                             remaining=max(0, len(pool) - len(results)))


def _mmr(rows: list[dict], profile: SkeletonProfile, basis: str, k: int) -> list[dict]:
    def base(r) -> float:
        sim = math.floor(r["m"].similarity / BAND) * BAND if basis == "pose" else 0.5
        return W_SIM * sim + W_FEAS * r["f"].score

    def tiebreak(r):
        return (r["f"].score, -DIFFICULTY_ORDER.get(r["c"].difficulty or "", 1), -r["c"].id)

    # How alike two catalog poses are, measured with the same matcher.
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
                return MMR_LAMBDA * base(r)
            redundancy = max(alike(r, s) for s in chosen)
            repeat = CATEGORY_NUDGE if r["c"].category in {s["c"].category for s in chosen} else 0.0
            duplicate = 1.0 if redundancy >= DUPLICATE else 0.0
            return MMR_LAMBDA * base(r) - (1 - MMR_LAMBDA) * redundancy - repeat - duplicate
        best = max(left, key=lambda r: (round(value(r), 6), tiebreak(r)))
        chosen.append(best)
        left.remove(best)
    return chosen
