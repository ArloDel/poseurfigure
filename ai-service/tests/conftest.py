from pathlib import Path

import pytest

from app.main import app, get_pipeline
from app.services.pipeline import Pipeline
from app.services.profiles import load_profiles
from tests.fakes import FakeClassifier, FakeDetector, FakeEstimator

PROFILES = load_profiles(Path(__file__).resolve().parents[2] / "shared" / "skeleton_profiles")


@pytest.fixture(autouse=True)
def fake_models():
    """API tests run the real pipeline code with fake models: no downloads, no inference."""
    detector = FakeDetector()
    app.dependency_overrides[get_pipeline] = lambda: Pipeline(detector, FakeClassifier(), FakeEstimator(), PROFILES)
    yield detector
    app.dependency_overrides.clear()
