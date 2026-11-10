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

    def classify(self, crop: Image.Image) -> dict[str, float]:
        import torch

        self._load()
        labels = list(PROMPTS)
        pixels = self._processor(images=crop, return_tensors="pt")
        with torch.inference_mode():
            image = _features(self._model.get_image_features(**pixels))
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
