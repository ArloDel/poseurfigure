"""Optional AI visual references (PRD 8.6): redraw the user's figure in a target pose, then check the result.

Providers implement `ImageGenerator` and are chosen with AI_GENERATION_PROVIDER:
  - "stub": development stand-in. No photo leaves the machine and nothing is billed.
  - "openai": OpenAI's image edit API. Sends the user's photo, the catalog reference photo and a stick figure
    of the target pose (AI_OPENAI_API_KEY, AI_OPENAI_IMAGE_MODEL, AI_OPENAI_IMAGE_QUALITY).
To add another, write a class with `name` and `generate()` and register it in `PROVIDERS`. API keys belong in
the environment, never in the repository.

Every generated image is validated: the same detector and pose model that read user photos read the generated
image, and the pose found is compared with the target. A plausible-looking image that doesn't show the target
pose is `rejected`. Validation says the picture shows the pose; it does not prove the figure can hold it.
"""
from __future__ import annotations

import base64
import io
from typing import Protocol

import httpx
from PIL import Image, ImageDraw

from app.schemas.analysis import FigureDetection, SkeletonProfile
from app.services.pipeline import Pipeline
from app.services.pose_extractor import build_pose
from app.services.pose_matcher import PoseView, _normalized, _similarity, match, mirror
from app.services.pose_sketch import draw_skeleton

MIN_JOINTS = 8  # visible joints needed in the generated image to judge its pose


class ImageGenerator(Protocol):
    name: str

    def generate(self, source: Image.Image, prompt: str, target: PoseView, profile: SkeletonProfile,
                 reference: Image.Image | None = None) -> Image.Image: ...


class GenerationFailed(Exception):
    """The provider didn't return an image. `retryable` is False when trying again can't help (refused, bad key)."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class StubGenerator:
    """Development stand-in: returns the source photo with a banner, so the whole flow (consent, queue,
    validation, labels) can be built and tested without a paid service. It never shows the target pose
    unless the figure was already in it, so validation usually, and correctly, rejects it."""

    name = "stub"

    def generate(self, source: Image.Image, prompt: str, target: PoseView, profile: SkeletonProfile,
                 reference: Image.Image | None = None) -> Image.Image:
        im = source.copy()
        im.thumbnail((768, 768))
        banner = 34
        out = Image.new("RGB", (im.width, im.height + banner), (20, 24, 70))
        out.paste(im, (0, 0))
        ImageDraw.Draw(out).text((10, im.height + 11), "DEVELOPMENT STUB - not a generated image", fill=(255, 216, 77))
        return out


def _png(image: Image.Image, side: int = 1024) -> bytes:
    im = image.convert("RGB")
    im.thumbnail((side, side))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class OpenAIGenerator:
    """OpenAI image edits (POST /v1/images/edits) with up to three input images: the user's figure, the catalog
    photo of the target pose, and a stick figure of that pose. One test on an eval photo kept the figure
    recognizable but mirrored the pose, so the prompt spells out left and right in picture terms, and
    validation accepts a mirrored result as such (see `validate`)."""

    name = "openai"
    URL = "https://api.openai.com/v1/images/edits"

    def __init__(self, api_key: str, model: str = "gpt-image-1-mini", quality: str = "medium",
                 size: str = "1024x1536", timeout: float = 120.0, client: httpx.Client | None = None):
        if not api_key:
            raise ValueError("AI_OPENAI_API_KEY is not set.")
        self.model, self.quality, self.size = model, quality, size
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def instructions(self, prompt: str, with_reference: bool) -> str:
        images = ("Image 1 is a photo of the user's action figure. Image 2 is a reference photo of a different figure "
                  "in the target pose. Image 3 is a stick figure of the same target pose: blue lines are the figure's "
                  "left side, orange lines its right side.") if with_reference else (
                  "Image 1 is a photo of the user's action figure. Image 2 is a stick figure of the target pose: blue "
                  "lines are the figure's left side, orange lines its right side.")
        return (f"{images} Make a new photo of the figure from image 1 in the target pose. Match the pose as it appears "
                "in the picture: a limb on the left side of the reference must be on the left side of your image, and "
                "a raised arm must be the same arm. Keep the figure from image 1 otherwise unchanged: same character, "
                "colors, armor, proportions and joint design. Do not copy the reference figure's look, colors or "
                f"background. Show the whole figure, head to feet. {prompt}")

    def generate(self, source: Image.Image, prompt: str, target: PoseView, profile: SkeletonProfile,
                 reference: Image.Image | None = None) -> Image.Image:
        inputs = [source] + ([reference] if reference is not None else []) + [draw_skeleton(target, profile)]
        files = [("image[]", (f"input{i}.png", _png(im), "image/png")) for i, im in enumerate(inputs, start=1)]
        data = {"model": self.model, "prompt": self.instructions(prompt, reference is not None),
                "quality": self.quality, "size": self.size, "n": "1"}
        try:
            res = self._client.post(self.URL, headers=self._headers, data=data, files=files)
        except httpx.HTTPError as exc:
            raise GenerationFailed(f"OpenAI request failed: {type(exc).__name__}") from exc
        if res.status_code != 200:
            try:
                err = res.json().get("error", {})
            except ValueError:
                err = {}
            # 400 (refused by moderation, bad input), 401/403 (key): another try gives the same answer.
            raise GenerationFailed(f"OpenAI returned {res.status_code}: {err.get('code') or err.get('type') or 'error'}",
                                   retryable=res.status_code == 429 or res.status_code >= 500)
        try:
            raw = base64.b64decode(res.json()["data"][0]["b64_json"])
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except (KeyError, IndexError, ValueError, OSError) as exc:
            raise GenerationFailed("OpenAI returned no readable image.") from exc


PROVIDERS: dict[str, type] = {"stub": StubGenerator, "openai": OpenAIGenerator}


def build_generator(provider: str, settings=None) -> ImageGenerator | None:
    if provider in ("", "none"):
        return None
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown generation provider '{provider}'. Known: none, {', '.join(sorted(PROVIDERS))}.")
    if provider == "openai":
        s = settings
        return OpenAIGenerator(s.openai_api_key, s.openai_image_model, s.openai_image_quality, s.openai_image_size,
                               s.generation_timeout)
    return PROVIDERS[provider]()


_MOVES = {
    "bend": "bent", "straighten": "straight", "raise": "raised", "raise_overhead": "raised overhead",
    "lower": "lowered at the side", "lift_leg": "lifted", "lean": "leaning",
}


def build_prompt(profile: SkeletonProfile, instructions: list[dict], mirrored: bool) -> str:
    """Text for the provider, per PRD 8.6: keep the figure, change only the pose."""
    steps = []
    for s in instructions:
        part = str(s.get("body_part", "")).replace("_", " ")
        if mirrored:
            part = part.replace("left", "\0").replace("right", "left").replace("\0", "right")
        move = _MOVES.get(str(s.get("movement", "")), str(s.get("movement", "")).replace("_", " "))
        angle = f" (about {round(s['target_angle'])} degrees)" if s.get("target_angle") is not None else ""
        steps.append(f"{part} {move}{angle}")
    pose = "; ".join(steps) if steps else "the pose shown by the reference skeleton"
    return (
        f"Redraw the same {profile.name.lower()} action figure from the photo in a new pose. "
        "Keep its identity, design, main colors and accessories. Keep the same number and arrangement of limbs. "
        f"Target pose: {pose}. Plain neutral background, photographed like a toy on a desk. "
        "Do not add text, logos or extra figures."
    )


def validate(image: Image.Image, target: PoseView, profile: SkeletonProfile, pipeline: Pipeline | None,
             min_similarity: float, max_joint_error: float) -> dict:
    """generated -> validated | rejected (PRD 8.6). `unvalidated` only when the models are switched off.

    Overall similarity is an average, so one badly wrong joint can hide behind many right ones (a standing
    figure scores ~0.89 against a crouch). Validation therefore also requires every joint angle both poses
    show to be within `max_joint_error` degrees.

    Image models sometimes draw the pose mirrored. That is checked separately: a result that passes only when
    flipped is `validated` with `mirrored: true`, so the app can say so ("shown mirrored").
    """
    if pipeline is None:
        return {"status": "unvalidated", "reason": "models_disabled", "similarity": None}

    dets = pipeline.detector.detect(image)
    if not dets:
        return {"status": "rejected", "reason": "no_figure", "similarity": None}
    figs = [FigureDetection(bbox=list(d.bbox), score=d.score) for d in dets]
    box = tuple(figs[pipeline.pick(figs)].bbox)
    pose = build_pose(pipeline.estimator.estimate(image, box), profile, image.size)
    found = PoseView(pose.keypoints, image.width / image.height)
    if len(_normalized(found)) < MIN_JOINTS:
        return {"status": "rejected", "reason": "pose_unreadable", "similarity": None}

    match(found, target, profile)  # fills in both views' joint angles

    def check(seen: PoseView, mirrored: bool) -> dict:
        sim, _, shared = _similarity(seen, target, profile)
        errors = {j: abs(seen.angles[j] - a) for j, a in target.angles.items() if j in seen.angles}
        worst = max(errors, key=errors.get) if errors else None
        ok = sim >= min_similarity and (worst is None or errors[worst] <= max_joint_error)
        return {"status": "validated" if ok else "rejected", "reason": None if ok else "pose_mismatch",
                "similarity": round(sim, 4), "mirrored": mirrored, "shared_joints": shared,
                "worst_joint": worst, "worst_joint_error": round(errors[worst], 1) if worst else None}

    straight, flipped = check(found, False), check(mirror(found), True)
    if straight["status"] == "validated" or flipped["status"] != "validated":
        # Neither passes: report the closer one, so the reason points at the real problem.
        if straight["status"] != "validated" and flipped["similarity"] > straight["similarity"] + 0.01:
            return flipped
        return straight
    return flipped
