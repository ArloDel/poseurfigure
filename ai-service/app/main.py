import asyncio
import base64
import io
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.config import Settings, get_settings
from app.schemas.analysis import (
    AnalyzeResponse, GenerateRequest, GenerateResponse, InspireRequest, RecommendRequest, RecommendResponse, SkeletonProfile,
)
from app.services.figure_identifier import FigureIdentifier, IdentifyFailed, build_identifier
from app.services.image_quality import UnreadableImage, assess, load_image
from app.services.image_generator import GenerationFailed, ImageGenerator, build_generator, build_prompt, validate
from app.services.inspiration import inspire
from app.services.pipeline import Pipeline
from app.services.pose_matcher import mirror, to_view
from app.services.recommender import rank
from app.services.profiles import load_profiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("figurepose.ai")

QUALITY_ONLY_VERSION = "quality-check-0.1"

# Inference is CPU-bound and already uses every core. Running two at once makes both several
# times slower (a retried request piling onto one that timed out took 133 s instead of 9 s),
# so requests wait their turn. Scale out with more AI service replicas, not concurrency.
_inference_slot = asyncio.Semaphore(1)


@lru_cache
def build_pipeline() -> Pipeline:
    """Real models, created once. They load lazily on first use (or at startup with AI_WARMUP)."""
    from app.models.figure_classifier import Siglip2Classifier
    from app.models.object_detector import Owlv2Detector
    from app.models.pose_estimator import VitPoseEstimator

    s = get_settings()
    return Pipeline(
        Owlv2Detector(threshold=s.detection_threshold, cache_dir=s.model_cache_dir),
        Siglip2Classifier(cache_dir=s.model_cache_dir),
        VitPoseEstimator(cache_dir=s.model_cache_dir),
        load_profiles(s.skeleton_profiles_path),
        min_profile_confidence=s.min_profile_confidence,
    )


def get_pipeline() -> Pipeline | None:
    return build_pipeline() if get_settings().models_enabled else None


def get_generator() -> ImageGenerator | None:
    s = get_settings()
    return build_generator(s.generation_provider, s)


def get_identifier() -> FigureIdentifier | None:
    s = get_settings()
    return build_identifier(s.identify_provider, s)


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.models_enabled and s.warmup:
        from PIL import Image

        from app.services.image_quality import assess as _assess

        t = time.perf_counter()
        img = Image.new("RGB", (640, 640), "white")
        await run_in_threadpool(build_pipeline().run, img, _assess(img, s))
        log.info("models warmed up in %.1fs", time.perf_counter() - t)
    yield


app = FastAPI(title="FigurePose AI", version=get_settings().version, lifespan=lifespan)


@app.middleware("http")
async def request_id(request: Request, call_next):
    """Carry the caller's request id through logs (PRD 15: request IDs)."""
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    log.info("%s %s %s %.0fms rid=%s", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000, rid)
    return response


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    profiles = load_profiles(settings.skeleton_profiles_path)
    return {"status": "ok", "service": settings.service_name, "version": settings.version,
            "models_enabled": settings.models_enabled, "generation_provider": settings.generation_provider,
            "identify_provider": settings.identify_provider,
            "profiles": sorted(profiles)}


@app.get("/v1/profiles")
def profiles(settings: Settings = Depends(get_settings)) -> list[SkeletonProfile]:
    return list(load_profiles(settings.skeleton_profiles_path).values())


@app.post("/v1/recommend")
def recommend_poses(request: RecommendRequest, settings: Settings = Depends(get_settings)) -> RecommendResponse:
    """Rank catalog poses for an analyzed figure (PRD 8.4). Geometry only, no models: fast and not queued."""
    known = load_profiles(settings.skeleton_profiles_path)
    if request.profile not in known:
        raise HTTPException(422, f"Unknown profile '{request.profile}'. Known: {', '.join(sorted(known))}.")
    return rank(request, known[request.profile])


@app.post("/v1/inspire")
def inspire_poses(request: InspireRequest, settings: Settings = Depends(get_settings)) -> RecommendResponse:
    """Pose ideas: the same character first, then figures that look alike, in poses unlike the figure's own."""
    known = load_profiles(settings.skeleton_profiles_path)
    if request.profile not in known:
        raise HTTPException(422, f"Unknown profile '{request.profile}'. Known: {', '.join(sorted(known))}.")
    return inspire(request, known[request.profile])


@app.post("/v1/identify")
async def identify_figure(
    image: UploadFile = File(...),
    bbox: str | None = Form(None),
    settings: Settings = Depends(get_settings),
    identifier: FigureIdentifier | None = Depends(get_identifier),
) -> dict:
    """Names the character the figure shows. `bbox` is the selected figure's box from /v1/analyze ([x0, y0, x1, y1],
    normalized); without it the whole photo is sent. A suggestion for the user to confirm."""
    if identifier is None:
        raise HTTPException(503, "Character recognition is not configured on this server.")
    data = await image.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {settings.max_upload_mb} MB.")
    try:
        img = load_image(data)
    except UnreadableImage as exc:
        raise HTTPException(422, str(exc)) from exc
    if bbox:
        try:
            x0, y0, x1, y1 = (float(v) for v in json.loads(bbox))
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
        except (ValueError, TypeError, AssertionError) as exc:
            raise HTTPException(422, "bbox must be [x0, y0, x1, y1] between 0 and 1.") from exc
        w, h = img.size
        # A little margin: the box can clip hands or a cape that help recognize the character.
        mx, my = (x1 - x0) * 0.05, (y1 - y0) * 0.05
        img = img.crop((max(0, x0 - mx) * w, max(0, y0 - my) * h, min(1, x1 + mx) * w, min(1, y1 + my) * h))
    try:
        result = await run_in_threadpool(identifier.identify, img)
    except IdentifyFailed as exc:
        log.warning("identify failed: %s", exc)
        raise HTTPException(502 if exc.retryable else 422, str(exc)) from exc
    return {"provider": identifier.name, **result}


@app.post("/v1/generate")
async def generate_visual(
    image: UploadFile = File(...),
    payload: str = Form(...),
    reference: UploadFile | None = File(None),
    settings: Settings = Depends(get_settings),
    pipeline: Pipeline | None = Depends(get_pipeline),
    generator: ImageGenerator | None = Depends(get_generator),
) -> GenerateResponse:
    """Optional AI visual (PRD 8.6): the user's figure in a target pose, then validated against that pose."""
    if generator is None:
        raise HTTPException(503, "AI visuals are not configured on this server.")
    try:
        request = GenerateRequest.model_validate_json(payload)
    except ValueError as exc:
        raise HTTPException(422, f"Invalid payload: {exc}") from exc
    known = load_profiles(settings.skeleton_profiles_path)
    if request.profile not in known:
        raise HTTPException(422, f"Unknown profile '{request.profile}'.")
    profile = known[request.profile]

    data = await image.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {settings.max_upload_mb} MB.")
    try:
        source = load_image(data)
    except UnreadableImage as exc:
        raise HTTPException(422, str(exc)) from exc

    # The catalog photo of the target pose, flipped along with the target when the user mirrors it.
    ref_img = None
    if reference is not None:
        try:
            ref_img = load_image(await reference.read(settings.max_upload_mb * 1024 * 1024))
        except UnreadableImage as exc:
            raise HTTPException(422, f"Reference: {exc}") from exc
        if request.mirrored:
            ref_img = ref_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    target = to_view(request.target.keypoints, request.target.image_size)
    if request.mirrored:
        target = mirror(target)
    prompt = build_prompt(profile, request.instructions, request.mirrored)

    # The provider call is network-bound: it runs outside the inference slot, so analyses aren't kept waiting.
    try:
        result = (await run_in_threadpool(generator.generate, source, prompt, target, profile, ref_img)).convert("RGB")
    except GenerationFailed as exc:
        log.warning("generation failed: %s", exc)
        raise HTTPException(502 if exc.retryable else 422, str(exc)) from exc

    async with _inference_slot:
        validation = await run_in_threadpool(validate, result, target, profile, pipeline,
                                             settings.validation_min_similarity, settings.validation_max_joint_error)

    buf = io.BytesIO()
    result.save(buf, "JPEG", quality=88)
    return GenerateResponse(provider=generator.name, prompt=prompt, image_base64=base64.b64encode(buf.getvalue()).decode(),
                            mime="image/jpeg", width=result.width, height=result.height, validation=validation)


@app.post("/v1/analyze")
async def analyze(
    image: UploadFile = File(...),
    profile: str | None = Form(None),
    figure_index: int | None = Form(None),
    settings: Settings = Depends(get_settings),
    pipeline: Pipeline | None = Depends(get_pipeline),
) -> AnalyzeResponse:
    known = load_profiles(settings.skeleton_profiles_path)
    if profile is not None and profile not in known:
        raise HTTPException(422, f"Unknown profile '{profile}'. Known: {', '.join(sorted(known))}.")

    data = await image.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {settings.max_upload_mb} MB.")

    try:
        img = load_image(data)
    except UnreadableImage as exc:
        raise HTTPException(422, str(exc)) from exc

    quality = assess(img, settings)
    if not quality.ok or pipeline is None:
        return AnalyzeResponse(model_version=pipeline.version if pipeline else QUALITY_ONLY_VERSION,
                               stage="quality_only", profile=profile, quality=quality)

    # Model inference is CPU-bound: keep it off the event loop, one at a time.
    async with _inference_slot:
        return await run_in_threadpool(pipeline.run, img, quality, profile, figure_index)
