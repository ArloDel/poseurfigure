"""Optional AI visual references (PRD 8.6): redraw the user's figure in a target pose, then check the result.

Providers implement `ImageGenerator`. Only a development stub ships: no photo leaves the machine and nothing
is billed. To add a real provider, write a class with `name` and `generate()`, register it in `PROVIDERS`,
and select it with AI_GENERATION_PROVIDER. Its API key belongs in the environment, never in the repository.

Every generated image is validated: the same detector and pose model that read user photos read the generated
image, and the pose found is compared with the target. A plausible-looking image that doesn't show the target
pose is `rejected`. Validation says the picture shows the pose; it does not prove the figure can hold it.
"""
from __future__ import annotations

from typing import Protocol

from PIL import Image, ImageDraw

from app.schemas.analysis import FigureDetection, SkeletonProfile
from app.services.pipeline import Pipeline
from app.services.pose_extractor import build_pose
from app.services.pose_matcher import PoseView, _normalized, match, mirror

MIN_JOINTS = 8  # visible joints needed in the generated image to judge its pose


class ImageGenerator(Protocol):
    name: str

    def generate(self, source: Image.Image, prompt: str, target: PoseView, profile: SkeletonProfile) -> Image.Image: ...


class StubGenerator:
    """Development stand-in: returns the source photo with a banner, so the whole flow (consent, queue,
    validation, labels) can be built and tested without a paid service. It never shows the target pose
    unless the figure was already in it, so validation usually, and correctly, rejects it."""

    name = "stub"

    def generate(self, source: Image.Image, prompt: str, target: PoseView, profile: SkeletonProfile) -> Image.Image:
        im = source.copy()
        im.thumbnail((768, 768))
        banner = 34
        out = Image.new("RGB", (im.width, im.height + banner), (20, 24, 70))
        out.paste(im, (0, 0))
        ImageDraw.Draw(out).text((10, im.height + 11), "DEVELOPMENT STUB - not a generated image", fill=(255, 216, 77))
        return out


PROVIDERS: dict[str, type] = {"stub": StubGenerator}


def build_generator(provider: str) -> ImageGenerator | None:
    if provider in ("", "none"):
        return None
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown generation provider '{provider}'. Known: none, {', '.join(sorted(PROVIDERS))}.")
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

    m = match(found, target, profile)  # also fills in both views' joint angles
    seen = mirror(found) if m.mirrored else found
    errors = {j: abs(seen.angles[j] - a) for j, a in target.angles.items() if j in seen.angles}
    worst = max(errors, key=errors.get) if errors else None
    ok = m.similarity >= min_similarity and (worst is None or errors[worst] <= max_joint_error)
    return {"status": "validated" if ok else "rejected", "reason": None if ok else "pose_mismatch",
            "similarity": m.similarity, "mirrored": m.mirrored, "shared_joints": m.shared_joints,
            "worst_joint": worst, "worst_joint_error": round(errors[worst], 1) if worst else None}
