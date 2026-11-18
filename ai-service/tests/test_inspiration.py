from app.schemas.analysis import InspireRequest
from app.services.inspiration import cosine, inspire
from tests.conftest import PROFILES
from tests.fakes import STANDING
from tests.test_generation import client
from tests.test_recommender import ARM_OUT, ARM_UP, ARM_UP_2, CROUCH, kps

H = PROFILES["humanoid_v1"]
SPIDEY = [1.0, 0.0, 0.0]
SPIDEY_ISH = [0.9, 0.436, 0.0]   # cosine ~0.9 with SPIDEY
ROBOT = [0.0, 0.0, 1.0]          # cosine 0


def req(cands, character=None, appearance=SPIDEY, pose=STANDING, **kw) -> InspireRequest:
    return InspireRequest(
        profile="humanoid_v1", character=character, appearance=appearance,
        pose={"keypoints": kps(pose), "image_size": [800, 800]} if pose else None,
        candidates=[{"id": i, "keypoints": kps(p), "image_size": [800, 800], "category": "action", "appearance": look,
                     "character": char} for i, p, look, char in cands],
        **kw)


def ids(resp):
    return [r.id for r in resp.results]


def test_same_character_comes_first_even_when_another_figure_looks_closer():
    resp = inspire(req([
        (1, ARM_UP, SPIDEY, "Iron Man"),                   # looks identical, other character
        (2, CROUCH, SPIDEY_ISH, "Spider-Man"),             # the same character
    ], character="Spider-Man (symbiote suit)"), H)
    assert ids(resp) == [2, 1]
    assert [r.group for r in resp.results] == ["same_character", "similar_look"]
    assert "same_character" in resp.results[0].reasons


def test_without_a_character_figures_that_look_alike_lead():
    resp = inspire(req([(1, ARM_UP, ROBOT, "Robot"), (2, CROUCH, SPIDEY_ISH, "Miles")]), H)
    assert ids(resp) == [2, 1]
    assert resp.results[0].group == "similar_look" and resp.results[1].group == "more"
    assert abs(resp.results[0].look - 0.9) < 0.01


def test_the_pose_the_figure_is_already_in_goes_down_the_list():
    # Both look the same; one is just the default standing pose the user photographed.
    resp = inspire(req([(1, STANDING, SPIDEY, None), (2, CROUCH, SPIDEY, None)]), H)
    assert ids(resp) == [2, 1]
    assert "new_pose" in resp.results[0].reasons and "new_pose" not in resp.results[1].reasons


def test_near_duplicate_poses_are_spread_out():
    resp = inspire(req([(1, ARM_UP, SPIDEY, None), (2, ARM_UP_2, SPIDEY, None), (3, ARM_OUT, SPIDEY_ISH, None)], top_k=2), H)
    assert set(ids(resp)) == {1, 3} or set(ids(resp)) == {2, 3}
    assert resp.remaining == 1


def test_steps_from_the_figure_come_with_each_idea():
    rec = inspire(req([(1, CROUCH, SPIDEY, None)]), H).results[0]
    knees = {c["joint"]: c["action"] for c in rec.changes if c["joint"].endswith("knee")}
    assert knees == {"left_knee": "bend", "right_knee": "bend"}


def test_without_a_readable_pose_or_look_it_still_answers():
    resp = inspire(req([(1, CROUCH, None, "Spider-Man"), (2, ARM_UP, None, None)], character="spider-man", appearance=None, pose=None), H)
    assert resp.basis == "type_only" and ids(resp) == [1, 2]
    assert resp.results[0].changes == [] and resp.results[0].look is None


def test_exclude_ids_and_endpoint():
    body = req([(1, CROUCH, SPIDEY, None), (2, ARM_UP, SPIDEY, None)], exclude_ids=[1]).model_dump()
    res = client.post("/v1/inspire", json=body)
    assert res.status_code == 200 and [r["id"] for r in res.json()["results"]] == [2]
    assert res.json()["matcher_version"] == "inspire-0.1"
    assert client.post("/v1/inspire", json=body | {"profile": "dragon"}).status_code == 422


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1.0 and cosine([1, 0], [0, 1]) == 0.0
    assert cosine(None, [1]) is None and cosine([1, 2], [1]) is None
