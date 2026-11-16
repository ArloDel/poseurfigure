"""End-to-end check of the main user journey against a running stack (PRD 19.1 "MVP Release").

    python tests/e2e/journey.py                      # dev stack on localhost:8000
    python tests/e2e/journey.py --base http://localhost:8080/api/v1 --photo path/to/figure.jpg

Uses only the standard library, so it runs anywhere Python 3.10+ does. It creates a guest device,
analyzes a photo, walks through the results, signs up (moving the guest's analysis to the account),
uses favorites and history, tries an AI visual if the server offers them, and deletes what it made.
Exits non-zero if any step fails.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHOTO = ROOT / "ai-service" / "datasets" / "eval_v1" / "images" / "013.jpg"
ACTIONS = {"keep", "bend", "straighten", "raise", "lower", "lift_leg", "lower_leg", "unknown"}


class Client:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body=None, photo: bytes | None = None, headers=None, url=None):
        h = {"Accept": "application/json", **(headers or {})}
        data = None
        if photo is not None:
            b = "----journey" + secrets.token_hex(8)
            data = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="figure.jpg"\r\n'
                    f'Content-Type: image/jpeg\r\n\r\n').encode() + photo + (
                    f'\r\n--{b}\r\nContent-Disposition: form-data; name="analysis_mode"\r\n\r\nautomatic\r\n--{b}--\r\n').encode()
            h["Content-Type"] = f"multipart/form-data; boundary={b}"
        elif body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url or self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw, code, ctype = r.read(), r.status, r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raw, code, ctype = e.read(), e.code, e.headers.get("Content-Type", "")
        return code, (json.loads(raw or b"{}") if "json" in ctype else raw)


class Journey:
    def __init__(self, client: Client):
        self.c = client
        self.failures = 0

    def check(self, name: str, ok: bool, detail=None) -> bool:
        if not ok:
            self.failures += 1
        suffix = f"  [{str(detail)[:300]}]" if detail is not None and not ok else ""
        print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}", flush=True)
        return ok

    def wait(self, path: str, headers: dict, done, seconds: int = 180) -> dict:
        r = {}
        for _ in range(seconds):
            _, r = self.c.call("GET", path, headers=headers)
            if done(r.get("data", {})):
                break
            time.sleep(1)
        return r.get("data", {})


def run(base: str, photo_path: Path) -> int:
    j = Journey(Client(base))
    call, check = j.c.call, j.check
    device = {"X-Guest-Key": str(uuid.uuid4())}

    # 1. The server is up.
    code, r = call("GET", "/health")
    if not check("health: API, database and AI service ready", code == 200 and r.get("success") is True, r):
        return 1
    visuals_on = bool(r["data"].get("features", {}).get("ai_visuals"))

    # 2. A photo that is too small is refused with a reason, before anything is stored.
    code, r = call("POST", "/analyses", photo=_tiny_jpeg(), headers=device)
    check("a too-small photo is refused (422) with a message", code == 422 and "image" in r.get("errors", {}), r)

    # 3. Guest analysis.
    code, r = call("POST", "/analyses", photo=photo_path.read_bytes(), headers=device)
    if not check("upload accepted at once (202)", code == 202, r):
        return 1
    aid = r["data"]["analysis_id"]
    t = time.perf_counter()
    a = j.wait(f"/analyses/{aid}", device, lambda d: d.get("status") in ("completed", "failed"))
    if not check(f"analysis completed in {time.perf_counter() - t:.0f}s", a.get("status") == "completed", a.get("error")):
        return 1
    recs = a["recommendations"]
    check(f"{len(recs)} recommendations for a {a['profile']} figure", len(recs) >= 3, len(recs))
    pose_basis = a.get("recommendation_basis") == "pose"
    check("each pick has reasons, and steps from the figure when ranked by pose",
          all(x["reasons"] for x in recs)
          and all((x["changes"] != []) == pose_basis and {c["action"] for c in x["changes"]} <= ACTIONS for x in recs))
    code, _ = call("GET", f"/analyses/{aid}", headers={"X-Guest-Key": str(uuid.uuid4())})
    check("another device can't open the analysis (404)", code == 404)

    # 4. Pose detail and "show different poses".
    first = recs[0]["pose"]
    code, r = call("GET", f"/poses/{first['id']}")
    check(f"pose detail '{first['name']}' has instructions", code == 200 and r["data"]["instructions"], r)
    shown = {x["pose"]["id"] for x in recs}
    if a.get("more_recommendations"):
        code, r = call("POST", f"/analyses/{aid}/recommendations", headers=device)
        new = {x["pose"]["id"] for x in r.get("data", {}).get("recommendations", [])}
        check("show different poses returns only new ones", code == 200 and new and not (new & shown), r)

    # 5. AI visual, only when the server offers them (stub provider in dev).
    if visuals_on:
        code, r = call("POST", f"/poses/{first['id']}/generate", {"analysis_id": aid}, headers=device)
        check("AI visual needs consent (422)", code == 422, r)
        code, r = call("POST", f"/poses/{first['id']}/generate", {"analysis_id": aid, "consent": True}, headers=device)
        if check("AI visual queued after consent (202)", code == 202 and r["data"]["ai_generated"] is True, r):
            v = j.wait(f"/generated-images/{r['data']['id']}", device, lambda d: d.get("status") != "pending")
            check(f"AI visual {v.get('status')}, validation {v.get('validation_status')}",
                  v.get("status") == "generated" and v.get("validation_status") in ("validated", "rejected"), v)
            if v.get("image_url"):
                code, img = call("GET", "", url=v["image_url"])
                check("signed image link serves a JPEG", code == 200 and isinstance(img, bytes) and img[:2] == b"\xff\xd8")
    else:
        print("SKIP AI visuals are off on this server", flush=True)

    # 6. Sign up on this device: the guest's analysis moves to the account.
    email = f"journey-{secrets.token_hex(5)}@example.test"
    password = secrets.token_urlsafe(12)
    code, r = call("POST", "/auth/register", {"name": "Journey check", "email": email, "password": password,
                                              "password_confirmation": password}, headers=device)
    if not check("account created", code in (200, 201) and r.get("data", {}).get("token"), r):
        return 1
    account = {"Authorization": f"Bearer {r['data']['token']}"}
    code, r = call("GET", "/analyses", headers=account)
    check("the guest's analysis is now in the account's history", code == 200 and aid in [x["analysis_id"] for x in r["data"]], r)

    # 7. Favorites.
    pid = first["id"]
    code, r = call("POST", "/favorites", {"pose_id": pid}, headers=account)
    check("save a recommended pose (201)", code == 201, r)
    code, _ = call("POST", "/favorites", {"pose_id": pid}, headers=account)
    check("saving it again is fine (200)", code == 200)
    code, r = call("GET", "/favorites", headers=account)
    fav = r.get("data", [])
    check("favorites list it, with its category", code == 200 and [f["pose"]["id"] for f in fav] == [pid] and fav[0]["pose"]["category"], r)
    code, _ = call("GET", "/favorites", headers=device)
    check("guests have no favorites (401)", code == 401)
    if fav:
        code, _ = call("DELETE", f"/favorites/{fav[0]['id']}", headers=account)
        check("remove the favorite", code == 200)

    # 8. Delete the analysis: it and its photo are gone.
    code, _ = call("DELETE", f"/analyses/{aid}", headers=account)
    check("delete the analysis", code == 200)
    code, _ = call("GET", f"/analyses/{aid}", headers=account)
    check("deleted analysis is gone (404)", code == 404)

    call("POST", "/auth/logout", headers=account)
    print(f"RESULT: {'ALL PASSED' if j.failures == 0 else f'{j.failures} FAILED'}", flush=True)
    return 0 if j.failures == 0 else 1


def _tiny_jpeg() -> bytes:
    """A valid 1x1 JPEG: real enough to reach the size check."""
    return bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f"
        "1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000"
        "010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105"
        "122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a43444546"
        "4748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aa"
        "b2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100"
        "003f00fbd3ffd9")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="http://localhost:8000/api/v1")
    p.add_argument("--photo", type=Path, default=DEFAULT_PHOTO)
    args = p.parse_args()
    sys.exit(run(args.base, args.photo))
