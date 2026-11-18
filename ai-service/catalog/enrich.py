"""Adds what pose ideas need to the built catalog: each figure's look and the character it shows.

usage (from ai-service/, after `python -m catalog.build`):
    python -m catalog.enrich              # appearance embeddings only (SigLIP 2, runs locally, free)
    python -m catalog.enrich --identify   # also ask the OpenAI vision model for characters not named yet (billed)

- appearance: SigLIP 2 image embedding of the figure's crop (figure_box), the same model and crop rule as user
  photos, so the two are comparable. Written to shared/catalog/appearance.json, one pose per line, so the
  readable poses.json stays small.
- character, variant, franchise: kept in manifest.json, the catalog's source of truth, so a rebuild keeps them.
  Names from --identify are suggestions: check them in the manifest and correct any that are wrong
  (character_source becomes "manual" once you edit one by hand; enrich never overwrites a set name).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from app.config import get_settings
from app.models.figure_classifier import Siglip2Classifier

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("manifest.json")
POSES = ROOT / "shared" / "catalog" / "poses.json"
APPEARANCE = ROOT / "shared" / "catalog" / "appearance.json"
PHOTOS = ROOT / "backend" / "public"


def crop(pose: dict) -> Image.Image:
    im = Image.open(PHOTOS / pose["image"]["path"]).convert("RGB")
    x0, y0, x1, y1 = pose.get("figure_box") or [0, 0, 1, 1]
    w, h = im.size
    return im.crop((x0 * w, y0 * h, x1 * w, y1 * h))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identify", action="store_true", help="name characters with the OpenAI vision model (billed)")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    catalog = json.loads(POSES.read_text(encoding="utf-8"))
    entries = {p["slug"]: p for p in manifest["poses"]}
    settings = get_settings()
    classifier = Siglip2Classifier(cache_dir=settings.model_cache_dir)
    identifier = None
    if args.identify:
        from app.services.figure_identifier import OpenAIIdentifier
        identifier = OpenAIIdentifier(settings.openai_api_key, settings.openai_vision_model)

    embeddings = {}
    for pose in catalog["poses"]:
        entry = entries[pose["slug"]]
        figure = crop(pose)
        pose.pop("appearance", None)
        embeddings[pose["slug"]] = classifier.embed(figure)
        if identifier is not None and not entry.get("character"):
            found = identifier.identify(figure)
            entry.update({"character": found["character"], "variant": found["variant"], "franchise": found["franchise"],
                          "character_source": f"ai:{found['model']}:{found['confidence']}"})
        for k in ("character", "variant", "franchise"):
            pose[k] = entry.get(k) or None
        print(f"{pose['slug']:24} {pose['character'] or '-':28} {pose['variant'] or '':22} {entry.get('character_source', '')}")

    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    POSES.write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f" {json.dumps(slug)}: {json.dumps(emb, separators=(',', ':'))}" for slug, emb in embeddings.items()]
    APPEARANCE.write_text('{"version": ' + json.dumps(classifier.version) + ', "embeddings": {\n' + ",\n".join(lines) + "\n}}\n",
                          encoding="utf-8")
    print(f"wrote {POSES.relative_to(ROOT)}, {APPEARANCE.relative_to(ROOT)} and {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
