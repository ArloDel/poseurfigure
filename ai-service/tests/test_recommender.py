from app.schemas.analysis import RecommendRequest
from app.services.pose_extractor import COCO17, RawPoint, map_to_profile
from app.services.recommender import rank
from tests.conftest import PROFILES
from tests.fakes import STANDING

H = PROFILES["humanoid_v1"]


def kps(points: dict, hidden: tuple = ()) -> dict:
    out = map_to_profile([RawPoint(*points[n], 0.05 if n in hidden else 0.9) for n in COCO17], H)
    return {n: {"x": k.x, "y": k.y, "visibility": k.visibility} for n, k in out.items()}


def req(query: dict, cands: list, **kw) -> RecommendRequest:
    return RecommendRequest(
        profile="humanoid_v1", pose={"keypoints": query, "image_size": [800, 800]},
        candidates=[{"id": i, "keypoints": kps(p), "image_size": [800, 800], "category": cat, "difficulty": diff}
                    for i, p, cat, diff in cands],
        **kw,
    )


ARM_UP = dict(STANDING, right_elbow=(0.40, 0.10), right_wrist=(0.40, 0.0))
ARM_UP_2 = dict(ARM_UP, right_wrist=(0.41, 0.01))  # practically the same pose
ARM_OUT = dict(STANDING, right_elbow=(0.25, 0.25), right_wrist=(0.10, 0.25))
CROUCH = dict(STANDING, left_knee=(0.62, 0.65), right_knee=(0.38, 0.65), left_ankle=(0.56, 0.78), right_ankle=(0.44, 0.78))
TIGHT_ELBOW = dict(STANDING, left_wrist=(0.60, 0.27))


def ids(resp):
    return [r.id for r in resp.results]


def test_near_duplicates_dont_fill_the_list():
    cands = [(1, ARM_UP, "action", "easy"), (2, ARM_UP_2, "action", "easy"), (3, CROUCH, "action", "easy")]
    score = rank(req(kps(ARM_UP), cands, top_k=2), H, strategy="score")
    hybrid = rank(req(kps(ARM_UP), cands, top_k=2), H)

    assert set(ids(score)) == {1, 2}  # v1: both copies of the same pose
    assert ids(hybrid)[0] in (1, 2) and ids(hybrid)[1] == 3  # v2: the second pick adds something new


def test_unshown_category_is_preferred_when_scores_are_close():
    cands = [(1, ARM_UP, "action", "easy"), (2, ARM_OUT, "action", "easy"), (3, ARM_OUT, "calm", "easy")]
    resp = rank(req(kps(ARM_UP), cands, top_k=2), H)
    assert ids(resp) == [1, 3]
    assert "different_category" in resp.results[1].reasons


def test_small_similarity_differences_dont_decide_the_order():
    # Same pose band: the easier pose wins regardless of a tiny similarity edge.
    cands = [(1, ARM_UP_2, "action", "hard"), (2, ARM_UP, "calm", "easy")]
    resp = rank(req(kps(dict(ARM_UP, right_wrist=(0.405, 0.005))), cands, top_k=2), H)
    assert ids(resp)[0] == 2


def test_unreadable_pose_falls_back_to_type_only():
    no_torso = kps(STANDING, hidden=("left_hip", "right_hip", "left_shoulder", "right_shoulder"))
    resp = rank(req(no_torso, [(1, ARM_UP, "action", "easy"), (2, CROUCH, "calm", "easy"), (3, TIGHT_ELBOW, "display", "easy")]), H)

    assert resp.basis == "type_only"
    assert all(r.similarity == 0.5 and not r.mirrored and "close_to_current" not in r.reasons for r in resp.results)
    assert resp.results[-1].id == 3  # the pose past a joint limit goes last


def test_exclude_ids_and_remaining():
    cands = [(i, STANDING, "action", "easy") for i in range(1, 7)]
    first = rank(req(kps(STANDING), cands, top_k=5), H)
    assert len(first.results) == 5 and first.remaining == 1

    more = rank(req(kps(STANDING), cands, top_k=5, exclude_ids=ids(first)), H)
    assert ids(more) == [i for i in range(1, 7) if i not in ids(first)]
    assert more.remaining == 0


def test_reasons_describe_each_pick():
    left_arm_up = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))
    resp = rank(req(kps(left_arm_up), [(1, ARM_UP, "action", "easy"), (2, TIGHT_ELBOW, "calm", "easy")]), H)
    by_id = {r.id: r for r in resp.results}

    assert {"close_to_current", "mirror"} <= set(by_id[1].reasons)
    assert "check_joints" in by_id[2].reasons


def test_scores_stay_comparable_to_v1():
    resp = rank(req(kps(STANDING), [(1, STANDING, "action", "easy")]), H)
    r = resp.results[0]
    assert r.score == round(0.7 * r.similarity + 0.3 * r.feasibility, 4)
