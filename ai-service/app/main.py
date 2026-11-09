import logging
import time
import uuid

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile

from app.config import Settings, get_settings
from app.schemas.analysis import AnalyzeResponse, SkeletonProfile
from app.services.image_quality import UnreadableImage, assess, load_image
from app.services.profiles import load_profiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("figurepose.ai")

MODEL_VERSION = "quality-check-0.1"

app = FastAPI(title="FigurePose AI", version=get_settings().version)


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
            "model_version": MODEL_VERSION, "profiles": sorted(profiles)}


@app.get("/v1/profiles")
def profiles(settings: Settings = Depends(get_settings)) -> list[SkeletonProfile]:
    return list(load_profiles(settings.skeleton_profiles_path).values())


@app.post("/v1/analyze")
async def analyze(
    image: UploadFile = File(...),
    profile: str | None = Form(None),
    settings: Settings = Depends(get_settings),
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
    # Sprint 4 adds detection, profile classification and keypoints after a passing quality check.
    return AnalyzeResponse(model_version=MODEL_VERSION, stage="quality_only", profile=profile, quality=quality, pose=None)
