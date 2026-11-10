from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file=".env", extra="ignore")

    service_name: str = "figurepose-ai"
    version: str = "0.1.0"
    # Shared with the Laravel seeder: one source of truth for skeleton profiles.
    skeleton_profiles_path: Path = Path(__file__).resolve().parents[2] / "shared" / "skeleton_profiles"
    max_upload_mb: int = 12
    # Quality thresholds (IMG-06 / IMG-09). Tune against real figure photos.
    min_dimension: int = 480
    min_sharpness: float = 60.0   # variance of the Laplacian on a 512px grayscale copy
    min_brightness: float = 45.0  # mean luminance, 0-255
    max_brightness: float = 235.0

    # Models (Sprint 4). Off = quality checks only, e.g. on a machine without the model cache.
    models_enabled: bool = True
    model_cache_dir: str | None = None  # defaults to the Hugging Face cache (HF_HOME)
    warmup: bool = False  # load models at startup so the first analysis isn't slow
    detection_threshold: float = 0.2
    # Below this, the app asks the user to confirm the figure type (FIG-03).
    min_profile_confidence: float = 0.6


@lru_cache
def get_settings() -> Settings:
    return Settings()
