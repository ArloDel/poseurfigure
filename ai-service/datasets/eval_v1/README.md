# eval_v1

Evaluation-only set for the Sprint 4 prototype. **Do not train on it**, or the numbers it produces stop meaning anything.

| | Count |
|---|---:|
| Photos | 38 (34 with figures, 4 without) |
| Figures with a box | 50 (plus 5 `ignore` regions) |
| Figures with keypoints | 18 (11 humanoid, 7 anime) |
| Profiles | `humanoid_v1` 16 photos, `anime_v1` 9, `mecha_v1` 9 |

Two of the photos without figures show real people, to check that people are not detected as figures.

## Files

- `images/`: photos resized to at most 1024 px. `006.jpg` is missing on purpose: its source was CC BY-ND, which does not allow resizing.
- `sources.json`: title, author, license and source page for every photo.
- `annotations.json`: generated labels. Do not edit; change `build_annotations.py` and run it.
- `build_annotations.py`: the labels and the labeling conventions.
- `preview_labels.py`: draws the labels on the photos to check them.

## Labeling

Labeled by hand on a 5% coordinate grid, so expect about ±2% error per point. Left and right are the figure's own sides. Hidden joints are left unlabeled rather than guessed. Accuracy is measured only on visible points.

This is a small, single-labeler set: good enough to compare approaches and catch regressions, not to claim production accuracy. PRD section 14 targets 500 to 1,000 images for the first real dataset.

## Licenses

All photos are CC BY, CC BY-SA, CC0 or public domain, from Flickr via Openverse. Attribution is in `sources.json`. Characters shown belong to their owners; the photos are used only to measure the models.
