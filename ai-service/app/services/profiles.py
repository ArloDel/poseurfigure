import json
from functools import lru_cache
from pathlib import Path

from app.schemas.analysis import SkeletonProfile


@lru_cache
def load_profiles(path: Path) -> dict[str, SkeletonProfile]:
    profiles = {}
    for file in sorted(path.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        profile = SkeletonProfile.model_validate(data)
        profiles[profile.profile] = profile
    return profiles
