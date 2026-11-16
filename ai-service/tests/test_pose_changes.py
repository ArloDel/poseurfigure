from app.services.recommender import rank
from tests.conftest import PROFILES
from tests.fakes import STANDING
from tests.test_recommender import ARM_UP, CROUCH, kps, req

H = PROFILES["humanoid_v1"]
LEFT_ARM_UP = dict(STANDING, left_elbow=(0.60, 0.10), left_wrist=(0.60, 0.0))


def by_joint(rec):
    return {c["joint"]: c for c in rec.changes}


def test_crouch_from_standing_bends_the_knees_and_keeps_the_rest():
    ch = by_joint(rank(req(kps(STANDING), [(1, CROUCH, "action", "easy")]), H).results[0])
    for knee in ("left_knee", "right_knee"):
        assert ch[knee]["action"] == "bend"
        assert ch[knee]["delta"] < -12 and ch[knee]["priority"] in ("medium", "high")
    for j in ("left_elbow", "right_elbow", "left_shoulder", "right_shoulder"):
        assert ch[j]["action"] == "keep"


def test_raising_an_arm_says_raise_and_the_reverse_says_lower():
    up = by_joint(rank(req(kps(STANDING), [(1, ARM_UP, "action", "easy")]), H).results[0])
    assert up["right_shoulder"]["action"] == "raise" and up["right_shoulder"]["priority"] == "high"
    down = by_joint(rank(req(kps(ARM_UP), [(1, STANDING, "action", "easy")]), H).results[0])
    assert down["right_shoulder"]["action"] == "lower"


def test_mirrored_match_uses_the_users_own_side():
    rec = rank(req(kps(LEFT_ARM_UP), [(1, ARM_UP, "action", "easy")]), H).results[0]
    assert rec.mirrored
    ch = by_joint(rec)
    # The user's left arm is already up: after mirroring, nothing to change on either arm.
    assert ch["left_shoulder"]["action"] == "keep" and ch["right_shoulder"]["action"] == "keep"


def test_hidden_joint_is_unknown_not_guessed():
    query = kps(STANDING, hidden=("left_ankle",))
    ch = by_joint(rank(req(query, [(1, CROUCH, "action", "easy")]), H).results[0])
    assert ch["left_knee"]["action"] == "unknown" and ch["left_knee"]["current"] is None
    assert ch["right_knee"]["action"] == "bend"


def test_type_only_basis_has_no_changes():
    few = kps(STANDING, hidden=tuple(n for n in STANDING if n not in ("nose", "left_eye")))
    resp = rank(req(few, [(1, CROUCH, "action", "easy")]), H)
    assert resp.basis == "type_only" and resp.results[0].changes == []
