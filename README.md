# FigurePose AI

Mobile posing assistant for action-figure collectors: snap a figure, get 3 to 5 pose ideas with joint-by-joint steps.
Product spec: [docs/PRD.md](docs/PRD.md). UI prototype: [design/ui-prototype.html](design/ui-prototype.html).

## Repository

```text
figurepose/
├── mobile/          Flutter app (Android, iOS, web, Windows)
├── backend/         Laravel 13 REST API + queue worker
├── ai-service/      Python FastAPI: photo checks, figure detection, type and keypoints
├── shared/          Skeleton profiles and the generated pose catalog, read by backend and AI service
├── infrastructure/  Postgres init SQL (nginx/ and docker/ reserved for later)
├── design/          Clickable UI prototype and stand-in photos (CC-licensed)
├── docs/            PRD
└── docker-compose.yml
```

## Requirements

| Tool | Version used | Needed for |
|---|---|---|
| Docker Desktop | Compose v2+ | API, worker, AI service, Postgres, Redis, SeaweedFS (S3) |
| Flutter | 3.47 stable (Dart 3.13) | Mobile app |
| PHP + Composer | PHP 8.4, Composer 2 | Running backend tests outside Docker (optional) |
| Python | 3.12+ | Running AI tests or the model evaluation outside Docker (optional) |

For Android builds you also need Android Studio (SDK + emulator). iOS builds need a Mac with Xcode.

## Run the stack

```bash
cp .env.example .env        # then change the passwords
docker compose up --build
```

On first start the API container runs migrations, seeds the three figure profiles and starter poses, and creates the private image bucket.

`backend/vendor` lives in the `backend_vendor` Docker volume, not the bind mount: reading it through a Windows bind mount made every request take 8+ seconds. After changing `composer.json`, rebuild and recreate that volume:

```bash
docker compose down && docker volume rm figurepose_backend_vendor && docker compose up --build
```

| Service | URL |
|---|---|
| API | http://localhost:8000/api/v1/health |
| AI service | http://localhost:8001/health (docs at /docs) |
| Object storage (S3 API) | http://localhost:8333, keys = `S3_ACCESS_KEY` / `S3_SECRET_KEY` |
| Postgres | localhost:5433, database `figurepose` |

### Try an upload

```bash
curl -s -X POST http://localhost:8000/api/v1/analyses \
  -H "Accept: application/json" \
  -H "X-Guest-Key: 3f1c2b9a-6a2e-4c1d-9d0e-2b7f4a1c8e55" \
  -F "image=@design/img/optimus-stance.jpg" \
  -F "analysis_mode=automatic"
```

Then poll `GET /api/v1/analyses/{analysis_id}` with the same `X-Guest-Key` until `status` is `completed` or `failed`.

## Run the mobile app

```bash
cd mobile
flutter pub get
flutter run -d chrome
```

The app talks to `http://localhost:8000/api/v1` by default. On an Android emulator, point it at the host machine:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

The browser build needs CORS: Laravel adds it for `api/*`, and the dev server's `backend/docker/router.php` adds it for catalog photos under `/catalog`.

To serve a release web build instead of `flutter run`:

```bash
cd mobile && flutter build web --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

```bash
python -m http.server 5180 --directory mobile/build/web
```

Then open http://localhost:5180.

**Screens.** Home (upload, server status), Discover (pose gallery with type, category and search filters), pose detail (steps by body region, joint warnings, save), Favorites, Profile (guest or account), History (with delete), sign-in / create account, and the analysis status screen. Guests can analyze and browse; favorites need an account.

## Tests

```bash
cd backend && php artisan test
```

```bash
cd ai-service && python -m pytest
```

AI tests use fake models, so they run in seconds without downloading anything.

```bash
cd mobile && flutter analyze && flutter test
```

Or run the backend and AI tests inside the containers. Backend tests always use an in-memory SQLite database: `phpunit.xml` overrides the container's Postgres settings, and the base `TestCase` refuses to run against anything else, so the dev database is never wiped.

```bash
docker compose exec api php artisan test
```

```bash
docker compose exec ai python -m pytest
```

## API

All endpoints are under `/api/v1` and return `{ "success": true, "data": ... }`.
Access: **open** needs nothing, **owner** needs a bearer token or `X-Guest-Key`, **account** needs a bearer token.

| Method | Endpoint | Access | Notes |
|---|---|---|---|
| GET | `/health` | open | API, database and AI service readiness |
| POST | `/auth/register` | open | `name`, `email`, `password` (8+ chars). Returns a token |
| POST | `/auth/login` | open | `email`, `password`. Returns a token. 5 tries per minute |
| POST | `/auth/logout` | account | Revokes the current token |
| GET | `/auth/me` | account | Current user |
| GET | `/figures/profiles` | open | `humanoid_v1`, `anime_v1`, `mecha_v1` |
| GET | `/figures` | account | The user's figures |
| POST | `/figures` | account | `name`, `figure_profile_id`, optional `brand`, `articulation_config` |
| GET | `/poses` | open | Catalog. Filters: `profile`, `category`, `q` |
| GET | `/poses/{id}` | open | Pose with structured instructions |
| POST | `/analyses` | owner | Multipart upload. Returns `202` with `analysis_id` at once |
| GET | `/analyses` | owner | History, newest first |
| GET | `/analyses/{analysis_id}` | owner | Status, quality report, errors |
| DELETE | `/analyses/{analysis_id}` | owner | Deletes the analysis and the stored photo |
| POST | `/analyses/{analysis_id}/profile` | owner | `figure_profile_id`. The user confirms or corrects the figure type; the photo is analyzed again with it |
| GET | `/favorites` | account | Saved catalog poses |
| POST | `/favorites` | account | `pose_id`. Saving twice keeps one favorite |
| DELETE | `/favorites/{id}` | account | Remove a favorite |

**Tokens.** Register and login return `data.token`. Send it as `Authorization: Bearer <token>`.

**Who owns an analysis.** Signed-in users send a Sanctum bearer token. Guests send `X-Guest-Key`: a UUID the app creates once and keeps in secure storage. The server stores only an HMAC of it. Anyone else gets `404`. If `X-Guest-Key` is sent with register or login, analyses made as a guest on that device move to the account.

**Lifecycle.** `pending → processing → completed`, or `failed`. An unsuitable photo (blurry, dark, too small, or no figure found) fails at once with a reason. An AI-service outage is retried 3 times, then fails with `retryable: true`.

**Analysis result.** A completed analysis returns `figures` (detected boxes), `selected_figure`, `classification` (type, confidence, `needs_confirmation`, `source`: `model` or `user`) and `pose`: 16 keypoints for humanoid and anime figures (19 for mecha, of which armor and backpack aren't estimated yet) with confidence and visibility, joint angles where three joints are visible, a rough camera view, and a pose embedding for matching in Sprint 5. Coordinates are normalized to the photo. Angles are 2D estimates.

## Environment variables

Root `.env` (Docker Compose):

| Variable | Purpose |
|---|---|
| `DB_PASSWORD` | Postgres password |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Object storage credentials, also used by Laravel's S3 disk |

Backend (`backend/.env`, overridden by Compose inside containers):

| Variable | Default | Purpose |
|---|---|---|
| `AI_SERVICE_URL` | `http://localhost:8001` | FastAPI base URL |
| `AI_SERVICE_TIMEOUT` | `30` | Seconds per AI call |
| `FIGUREPOSE_IMAGE_DISK` | `s3` | Disk for user photos (private) |
| `UPLOAD_MAX_KB` | `10240` | Max photo size |
| `UPLOAD_MIN_DIMENSION` / `UPLOAD_MAX_DIMENSION` | `480` / `8000` | Pixel limits per side |
| `ANALYSIS_MAX_ATTEMPTS` | `3` | Retries when the AI service fails |
| `SKELETON_PROFILES_PATH` | `../shared/skeleton_profiles` | Profile JSON used by the seeder |

AI service (prefix `AI_`): `AI_SKELETON_PROFILES_PATH`, `AI_MIN_SHARPNESS` (60), `AI_MIN_BRIGHTNESS` (45), `AI_MAX_BRIGHTNESS` (235), `AI_MIN_DIMENSION` (480), `AI_MAX_UPLOAD_MB` (12), `AI_MODELS_ENABLED` (true; false = photo checks only), `AI_WARMUP` (false; true in Compose), `AI_MODEL_CACHE_DIR` (Hugging Face cache by default), `AI_DETECTION_THRESHOLD` (0.2), `AI_MIN_PROFILE_CONFIDENCE` (0.6, below it the app asks the user to confirm the type).

Backend: `AI_SERVICE_TIMEOUT` is 60 s in Compose, since CPU inference takes about 10 s per photo.

Mobile (`--dart-define`): `API_BASE_URL`.

## Sprint 1 status

- [x] Repository and project structure
- [x] Laravel + PostgreSQL (pgvector image, extension enabled)
- [x] Migrations for all PRD tables, seeders for 3 profiles and 7 starter poses
- [x] FastAPI with `/health`, `/v1/profiles` and image quality checks
- [x] Flutter app with theme, 4-tab navigation, Home screen, upload and status polling
- [x] Docker Compose for local development
- [x] Photo-upload endpoint with async queue processing
- [x] README with setup and environment variables

## Sprint 2 status

- [x] Register, login, logout and current-user endpoints (Sanctum tokens)
- [x] Login and register rate limiting
- [x] Guest analyses move to the account on sign-in
- [x] Figures: list and add, with optional joint limits
- [x] Favorites: save, list, remove
- [x] Analysis history, and delete with photo cleanup

## Sprint 3 status

- [x] Catalog poses carry a photo URL and credit; photos are served from `backend/public/catalog`
- [x] Mobile sign-in and create account, token in secure storage, guest mode by default
- [x] Pose gallery with type, category and search filters
- [x] Pose detail with steps grouped by body region, joint warnings and photo credit
- [x] Favorites, Profile and History screens backed by the Sprint 2 API
- [x] 20 widget and unit tests with fake repositories
- [x] Dev API responds in under 0.5 s (OPcache, vendor in a Docker volume)

## Sprint 4 status

- [x] Figure detection (OWLv2), figure type (SigLIP 2) and keypoints (ViTPose), all Apache-2.0, revisions pinned
- [x] Keypoints mapped to the shared skeleton profiles, with visibility, joint angles, camera view and a pose embedding
- [x] Photos with no figure fail with a clear reason; an unsure type asks the user to confirm and re-runs (FIG-03)
- [x] Hand-labeled evaluation set (38 CC-licensed photos) and an evaluation script with a baseline report
- [x] App shows the figure type, joints found, hidden joints and angles, with the skeleton drawn on the photo
- [x] Runs on CPU in Docker, one inference at a time, about 10 s per photo

## Sprint 5 status

- [x] Pose catalog of 25 poses from CC-licensed photos, keypoints extracted with the same models as user photos; 20 pass the quality gate (9 humanoid, 8 anime, 3 mecha)
- [x] Instructions and joint-limit warnings generated from each pose's angles; shoulder and hip limits added to the profiles
- [x] Matching per PRD 8.4 (angle 40%, position 35%, embedding 25%), mirrored poses recognized, feasibility against profile or figure limits
- [x] `POST /v1/recommend` in the AI service; the backend stores the top 5 per analysis before marking it completed
- [x] Matching evaluation with a baseline report

Not yet built (later sprints): recommendation screen in the app, diversity in ranking, AI image generation, Google sign-in, crop and rotate before upload, a figure-specific keypoint model (needs a training dataset).

## Pose catalog and matching

The catalog's source of truth is `ai-service/catalog/manifest.json` (photo, crop, name, type, category, difficulty, credit). Rebuild it with:

```bash
cd ai-service && python -m catalog.build
```

That downloads and crops the photos into `backend/public/catalog/`, extracts keypoints, angles, instructions and limit warnings, and writes `shared/catalog/poses.json`. A pose is published only if its neck and both hips and at least 10 joints are visible. Then reseed: `docker compose exec api php artisan db:seed --class=PoseCatalogSeeder --force`.

Recommendations are ranked by `0.7 × similarity + 0.3 × feasibility`. Baseline (full report: [ai-service/reports/match_v1.md](ai-service/reports/match_v1.md)):

| Measure | Result |
|---|---|
| Catalog photo reframed or mirrored, found at rank 1 | 19/20 each (top 3: 20/20) |
| Mirrored photo flagged as mirrored | 19/20 |
| Same top pose from labeled vs predicted keypoints | 8/18 (top-5 overlap 72%) |
| Matching time | ~6 ms for one pose against a profile's catalog |

Known limits: the catalog is small (only 3 mecha poses, since the pose model struggles with winged or flying mecha). Rankings are sensitive to keypoint errors because many poses score close together. When a figure's torso isn't readable, every pose scores 0.5 and the order means nothing; Sprint 6 should say so in the app instead of ranking. Five catalog photos are also eval_v1 photos.

## AI models and evaluation

| Step | Model | License |
|---|---|---|
| Find figures | `google/owlv2-base-patch16-ensemble` (zero-shot detection) | Apache-2.0 |
| Figure type | `google/siglip2-base-patch16-224` (zero-shot, prompt ensemble) | Apache-2.0 |
| Keypoints | `usyd-community/vitpose-base-simple` (COCO-17, mapped to our profiles) | Apache-2.0 |

All three are used as-is, without training on figures. Revisions are pinned in `ai-service/app/models/registry.py`. OpenAI CLIP was not used: its model card rules out deployed use.

Baseline on `eval_v1` (full report: [ai-service/reports/eval_v1.md](ai-service/reports/eval_v1.md)):

| Measure | Result | PRD target |
|---|---|---|
| Main figure found | 33/34 photos (97%) | ≥ 85% |
| Detection precision / recall | 92% / 98% | |
| Photos without figures (incl. real people) left empty | 4/4 | |
| Figure type, end to end | 32/34 (94%) | |
| Keypoints within 10% of figure size (PCK@0.1) | 90% | measured prototype |
| Time per photo, CPU | ~9 s (8.7 s mean on a 12-thread desktop) | ≤ 15 s |

Known limits: the set is small and labeled by one person, so treat these as a baseline, not production accuracy. ViTPose is a model for people; it works well on humanoid figures but has no armor or backpack points for mecha. The type classifier is rarely unsure, so it seldom asks the user to confirm even when it is wrong (2 humanoid figures read as anime). Loose accessories next to a figure can show up as extra detections.

To run the evaluation locally (downloads ~1.3 GB of models on first run):

```bash
cd ai-service && pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-dev.txt
```

```bash
cd ai-service && python -m eval.run_eval
```

## Production notes

The Compose file is for development: PHP's built-in server, source mounted into containers, no TLS. Before deploying: serve `/catalog` from nginx or a CDN with an `Access-Control-Allow-Origin` header, add nginx + PHP-FPM, pin every image by digest, use real secret management, put Postgres/Redis/storage on a private network, add backups and monitoring. Object storage is a single-node SeaweedFS (`chrislusf/seaweedfs:4.53`) because MinIO no longer publishes container images; in production use a managed S3 bucket or a replicated SeaweedFS setup. The Laravel side only speaks S3, so switching needs env changes only.

## Credits

Stand-in photos in `design/img` and `mobile/assets/images` are CC-licensed or public-domain photos from Flickr, found via Openverse. Authors and licenses are in `design/img/credits.json`. Fonts: Bowlby One and Archivo, SIL Open Font License (`mobile/assets/fonts`).
