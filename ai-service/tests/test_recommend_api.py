from fastapi.testclient import TestClient

from app.main import app
from app.services.pose_extractor import COCO17, RawPoint, map_to_profile
from tests.conftest import PROFILES
from tests.fakes import STANDING

client = TestClient(app)


def keypoints(points: dict) -> dict:
    kps = map_to_profile([RawPoint(*points[n], 0.9) for n in COCO17], PROFILES["humanoid_v1"])
    return {n: {"x": k.x, "y": k.y, "visibility": k.visibility} for n, k in kps.items()}


ARM_UP = dict(STANDING, right_elbow=(0.40, 0.10), right_wrist=(0.40, 0.0))
LEFT_ARM_UP = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))
TIGHT_ELBOW = dict(STANDING, left_wrist=(0.60, 0.27))  # forearm folded flat against the upper arm


def request(candidates, **extra):
    return {"profile": "humanoid_v1", "pose": {"keypoints": keypoints(STANDING), "image_size": [800, 800]},
            "candidates": [{"id": i, "keypoints": keypoints(p), "image_size": [800, 800]} for i, p in candidates], **extra}


def test_ranks_closest_pose_first_and_limits_to_top_k():
    res = client.post("/v1/recommend", json=request([(1, ARM_UP), (2, STANDING), (3, TIGHT_ELBOW)], top_k=2))
    assert res.status_code == 200
    body = res.json()
    assert body["matcher_version"] == "match-0.1"
    assert [r["id"] for r in body["results"]] == [2, 1]
    top = body["results"][0]
    assert top["similarity"] > 0.99 and top["feasibility"] == 1.0
    assert set(top["components"]) == {"angle", "position", "embedding"}


def test_reports_mirroring_and_joint_limit_warnings():
    body = client.post("/v1/recommend", json={**request([(1, LEFT_ARM_UP), (2, TIGHT_ELBOW)]),
                                              "pose": {"keypoints": keypoints(ARM_UP), "image_size": [800, 800]}}).json()
    by_id = {r["id"]: r for r in body["results"]}
    assert by_id[1]["mirrored"] is True
    assert by_id[2]["warnings"][0]["joint"] == "left_elbow"
    assert by_id[2]["feasibility"] < 1.0


def test_figure_limits_change_feasibility():
    stiff = {"left_shoulder": {"min": 0, "max": 60}}
    body = client.post("/v1/recommend", json=request([(1, dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0)))],
                                                     figure_limits=stiff)).json()
    assert body["results"][0]["warnings"][0]["limit_source"] == "figure"


def test_unknown_profile_is_rejected():
    assert client.post("/v1/recommend", json={**request([]), "profile": "dragon_v9"}).status_code == 422


def test_empty_catalog_returns_no_results():
    assert client.post("/v1/recommend", json=request([])).json()["results"] == []
