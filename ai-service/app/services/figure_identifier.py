"""Names the character a figure shows ("Spider-Man (symbiote suit)"), so pose ideas can show the same
character first. A guess the user confirms or corrects, never a fact.

Providers are chosen with AI_IDENTIFY_PROVIDER: "none" (off: the user types the name) or "openai" (a vision
model reads the figure crop). Sending the photo to OpenAI needs the user's consent; the backend checks it.
"""
from __future__ import annotations

import base64
import io
import json
import re
from typing import Protocol

import httpx
from PIL import Image

PROMPT = (
    "This is a photo of a collectible action figure or model kit. Name the character it depicts, the franchise, "
    "and the costume or variant if it is a specific one (for example 'symbiote suit'). If you can tell, add the "
    "figure line or maker (for example 'MAFEX', 'Figma', 'S.H.Figuarts'). Use the most common English name. "
    "If you can't tell who it is, leave character empty and set confidence to 'low'. Leave any field you can't "
    "tell empty. Judge the figure itself, not stands, boxes or logos around it: a stand's logo can belong to "
    "another character."
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "character": {"type": "string"},
        "variant": {"type": "string"},
        "franchise": {"type": "string"},
        "figure_line": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["character", "variant", "franchise", "figure_line", "confidence"],
}


class IdentifyFailed(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class FigureIdentifier(Protocol):
    name: str

    def identify(self, crop: Image.Image) -> dict: ...


def character_key(name: str | None) -> str:
    """Comparable form of a character name: "Spider-Man (Symbiote Suit)" and "spiderman" both give "spiderman".
    Variants in brackets are dropped, so a symbiote Spider-Man still counts as the same character."""
    if not name:
        return ""
    base = re.sub(r"\(.*?\)", " ", name.lower())
    return re.sub(r"[^a-z0-9]", "", base)


class OpenAIIdentifier:
    name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-5.4", timeout: float = 45.0, client: httpx.Client | None = None):
        if not api_key:
            raise ValueError("AI_OPENAI_API_KEY is not set.")
        self.model = model
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def identify(self, crop: Image.Image) -> dict:
        im = crop.convert("RGB")
        im.thumbnail((768, 768))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": url, "detail": "low"}},
            ]}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "figure", "strict": True, "schema": SCHEMA}},
        }
        try:
            res = self._client.post(self.URL, headers=self._headers, json=body)
        except httpx.HTTPError as exc:
            raise IdentifyFailed(f"OpenAI request failed: {type(exc).__name__}") from exc
        if res.status_code != 200:
            try:
                err = res.json().get("error", {})
            except ValueError:
                err = {}
            raise IdentifyFailed(f"OpenAI returned {res.status_code}: {err.get('code') or err.get('type') or 'error'}",
                                 retryable=res.status_code == 429 or res.status_code >= 500)
        try:
            msg = res.json()["choices"][0]["message"]
            if msg.get("refusal"):
                raise IdentifyFailed("OpenAI declined to describe this photo.", retryable=False)
            data = json.loads(msg["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise IdentifyFailed("OpenAI returned no readable answer.") from exc
        return normalize(data, self.model)


def normalize(data: dict, model: str) -> dict:
    """Trimmed fields, a display name ("Spider-Man (symbiote suit)") and its comparable key."""
    out = {k: str(data.get(k) or "").strip() for k in ("character", "variant", "franchise", "figure_line")}
    for k, v in out.items():
        if v.lower() in ("unknown", "n/a", "none", "unsure"):
            out[k] = ""
    out["confidence"] = data.get("confidence") if data.get("confidence") in ("high", "medium", "low") else "low"
    if not out["character"]:
        out["confidence"] = "low"
    out["display_name"] = f"{out['character']} ({out['variant']})" if out["character"] and out["variant"] else out["character"]
    out["key"] = character_key(out["character"])
    out["model"] = model
    return out


def build_identifier(provider: str, settings=None) -> FigureIdentifier | None:
    if provider in ("", "none"):
        return None
    if provider == "openai":
        return OpenAIIdentifier(settings.openai_api_key, settings.openai_vision_model, settings.identify_timeout)
    raise ValueError(f"Unknown identify provider '{provider}'. Known: none, openai.")
