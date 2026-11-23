"""Figure type classification with SigLIP 2 (zero-shot). FIG-02, FIG-03."""
from __future__ import annotations

import threading
from typing import Protocol

from PIL import Image

from app.models.registry import CLASSIFIER


class FigureClassifier(Protocol):
    version: str

    def classify(self, crop: Image.Image) -> dict[str, float]:
        """Probability per profile slug, summing to 1."""
        ...

    def embed(self, crop: Image.Image) -> list[float]:
        """The figure's look as a unit vector: figures that look alike (same character, same suit) are close."""
        ...

    def photo_kind(self, crop: Image.Image) -> dict[str, float]:
        """Whether a found picture is a photo of a real toy: probability per kind in PHOTO_KINDS."""
        ...


# Several phrasings per profile; their logits are averaged (prompt ensembling).
PROMPTS: dict[str, list[str]] = {
    "humanoid_v1": [
        "a photo of an action figure of a person",
        "a photo of a superhero action figure",
        "a photo of a realistic human figurine",
    ],
    "anime_v1": [
        "a photo of an anime figure",
        "a photo of a Japanese anime character figurine",
        "a photo of a manga style figure with big eyes",
    ],
    "mecha_v1": [
        "a photo of a robot model kit",
        "a photo of a mecha robot figure",
        "a photo of a transforming robot toy",
    ],
}


# What a found picture shows (Pinterest references): only photos of real toys are kept as pose ideas.
# Several phrasings per kind, averaged; the probability of "figure" is the softmax over the kinds.
PHOTO_KINDS: dict[str, list[str]] = {
    "figure": [
        "a photo of an action figure toy",
        "a photo of a posable collectible figure",
        "a product photo of a toy figure with visible joints",
    ],
    "render": ["a 3D render of a character", "a video game screenshot", "a CGI image of a superhero"],
    "illustration": ["a drawing of a character", "comic book art", "a digital painting"],
    "statue": ["a photo of a collectible statue on a decorative base", "a photo of a resin statue"],
    "person": ["a photo of a person in a costume", "a cosplay photo", "a movie still of an actor"],
}


def _features(out):
    """L2-normalized embeddings. get_*_features returns a tensor or, in some versions, a model output."""
    t = out if hasattr(out, "norm") else getattr(out, "pooler_output", out[0])
    return t / t.norm(dim=-1, keepdim=True)


class Siglip2Classifier:
    version = CLASSIFIER.tag

    def __init__(self, cache_dir: str | None = None):
        self._cache_dir = cache_dir
        self._lock = threading.Lock()
        self._model = self._processor = self._text = None
        # The last crop's image features: classify() and embed() run on the same crop, encode it once.
        self._last: tuple[int, object] | None = None

    def _load(self):
        with self._lock:
            if self._model is None:
                import torch
                from transformers import AutoModel, AutoProcessor

                self._processor = AutoProcessor.from_pretrained(CLASSIFIER.repo, revision=CLASSIFIER.revision, cache_dir=self._cache_dir)
                self._model = AutoModel.from_pretrained(CLASSIFIER.repo, revision=CLASSIFIER.revision, cache_dir=self._cache_dir).eval()
                # The prompts never change: encode them once instead of on every photo.
                texts = [p for lab in PROMPTS for p in PROMPTS[lab]]
                tokens = self._processor(text=texts, padding="max_length", max_length=64, return_tensors="pt")
                with torch.inference_mode():
                    self._text = _features(self._model.get_text_features(**tokens))

    def _image(self, crop: Image.Image):
        import torch

        self._load()
        if self._last is not None and self._last[0] == id(crop):
            return self._last[1]
        pixels = self._processor(images=crop, return_tensors="pt")
        with torch.inference_mode():
            image = _features(self._model.get_image_features(**pixels))
        self._last = (id(crop), image)
        return image

    def embed(self, crop: Image.Image) -> list[float]:
        return [round(v, 5) for v in self._image(crop)[0].tolist()]

    def photo_kind(self, crop: Image.Image) -> dict[str, float]:
        """Probability per kind in PHOTO_KINDS (figure, render, illustration, statue, person), summing to 1."""
        import torch

        image = self._image(crop)
        with self._lock:
            if getattr(self, "_kind_text", None) is None:
                texts = [p for k in PHOTO_KINDS for p in PHOTO_KINDS[k]]
                tokens = self._processor(text=texts, padding="max_length", max_length=64, return_tensors="pt")
                with torch.inference_mode():
                    self._kind_text = _features(self._model.get_text_features(**tokens))
        with torch.inference_mode():
            logits = (image @ self._kind_text.T)[0] * self._model.logit_scale.exp() + self._model.logit_bias
        per, i = [], 0
        for k in PHOTO_KINDS:
            n = len(PHOTO_KINDS[k])
            per.append(logits[i:i + n].mean())
            i += n
        probs = torch.softmax(torch.stack(per), dim=0).tolist()
        return {k: round(p, 4) for k, p in zip(PHOTO_KINDS, probs)}

    def classify(self, crop: Image.Image) -> dict[str, float]:
        import torch

        labels = list(PROMPTS)
        image = self._image(crop)
        with torch.inference_mode():
            # Same formula as SigLIP's forward pass: scaled cosine similarity plus bias.
            logits = (image @ self._text.T)[0] * self._model.logit_scale.exp() + self._model.logit_bias
        per_label, i = [], 0
        for lab in labels:
            n = len(PROMPTS[lab])
            per_label.append(logits[i:i + n].mean())
            i += n
        # The profiles are exclusive, so softmax across them (SigLIP's own sigmoid scores are independent).
        probs = torch.softmax(torch.stack(per_label), dim=0).tolist()
        return {lab: round(p, 4) for lab, p in zip(labels, probs)}
