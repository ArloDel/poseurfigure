import asyncio
import base64
import io
import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.schemas.analysis import (
    AnalyzeResponse, GenerateRequest, GenerateResponse, RecommendRequest, RecommendResponse, SkeletonProfile,
)
from app.services.image_quality import UnreadableImage, assess, load_image
from app.services.image_generator import ImageGenerator, build_generator, build_prompt, validate
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
    return build_generator(get_settings().generation_provider)


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


@app.post("/v1/generate")
async def generate_visual(
    image: UploadFile = File(...),
    payload: str = Form(...),
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

    target = to_view(request.target.keypoints, request.target.image_size)
    if request.mirrored:
        target = mirror(target)
    prompt = build_prompt(profile, request.instructions, request.mirrored)

    def work():
        result = generator.generate(source, prompt, target, profile).convert("RGB")
        return result, validate(result, target, profile, pipeline, settings.validation_min_similarity,
                                settings.validation_max_joint_error)

    async with _inference_slot:
        result, validation = await run_in_threadpool(work)

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
