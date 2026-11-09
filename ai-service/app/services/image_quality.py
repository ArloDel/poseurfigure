"""Image quality checks run before any model sees the photo (IMG-06, IMG-09)."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings
from app.schemas.analysis import QualityIssue, QualityReport

_LAPLACIAN = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)


class UnreadableImage(ValueError):
    pass


def load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise UnreadableImage("The file is not a readable image.") from exc
    # Phone photos often store rotation in EXIF; apply it so width/height are what the user sees.
    return ImageOps.exif_transpose(image).convert("RGB")


def _laplacian_variance(gray: np.ndarray) -> float:
    padded = np.pad(gray, 1, mode="edge")
    h, w = gray.shape
    out = np.zeros_like(gray)
    for dy in range(3):
        for dx in range(3):
            k = _LAPLACIAN[dy, dx]
            if k:
                out += k * padded[dy:dy + h, dx:dx + w]
    return float(out.var())


def assess(image: Image.Image, settings: Settings) -> QualityReport:
    width, height = image.size

    # Measure on a fixed-size copy so the score doesn't depend on camera resolution.
    small = image.copy()
    small.thumbnail((512, 512))
    gray = np.asarray(small.convert("L"), dtype=np.float32)
    sharpness = _laplacian_variance(gray)
    brightness = float(gray.mean())

    issues: list[QualityIssue] = []
    if min(width, height) < settings.min_dimension:
        issues.append(QualityIssue(code="too_small", message=f"The photo is too small. Use at least {settings.min_dimension} px on the short side."))
    if sharpness < settings.min_sharpness:
        issues.append(QualityIssue(code="blurry", message="This photo is too blurry to read the joints. Hold the phone still or rest it on something."))
    if brightness < settings.min_brightness:
        issues.append(QualityIssue(code="too_dark", message="This photo is too dark. Add light from the front."))
    elif brightness > settings.max_brightness:
        issues.append(QualityIssue(code="too_bright", message="This photo is overexposed. Move away from direct light."))

    return QualityReport(
        ok=not issues, width=width, height=height,
        sharpness=round(sharpness, 1), brightness=round(brightness, 1), issues=issues,
    )
