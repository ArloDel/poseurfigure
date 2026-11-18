# Deploying FigurePose

The project is not online yet. This is the checklist for when it goes on a server, and the same steps
run the production-like stack on a development machine (`http://localhost:8080`).

## What runs

| Service | Image | Published | Notes |
|---|---|---|---|
| web | `infrastructure/nginx/Dockerfile` | `WEB_PORT` (8080) | Web app, `/api` to PHP-FPM, `/catalog` photos, JSON access log with request IDs |
| api | `backend/Dockerfile.prod` | no | PHP-FPM, runs migrations and seeders on start |
| worker | same image as api | no | Queue: analyses and AI visuals |
| ai | `ai-service/Dockerfile` | no | Models load at start; first start downloads about 1.3 GB |
| postgres, redis, storage | pinned by digest | no | Data in named volumes |

Server size: 4 vCPU and 8 GB RAM is the floor. The AI service alone uses 1 to 4 GB, and CPU inference
takes 8 to 12 s per photo with one photo processed at a time.

## First start

1. Copy `.env.prod.example` to `.env.prod` and fill every secret. Never commit it.
   - `DB_PASSWORD`, `S3_SECRET_KEY`: `openssl rand -base64 24`
   - `APP_KEY`: `base64:` followed by 32 random bytes in base64 (`echo "base64:$(openssl rand -base64 32)"`)
   - `APP_URL`: the address users open, for example `https://figurepose.example`
2. Build the web app: `sh infrastructure/scripts/build-web.sh`
3. Start: `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build`
4. Wait until every service is healthy: `docker compose -f docker-compose.prod.yml --env-file .env.prod ps`
5. Smoke test: `python tests/e2e/journey.py --base <APP_URL>/api/v1`
   It creates a test account (`journey-…@example.test`) and deletes its analysis, but not the account.

## Updating

1. `git pull`, then steps 2, 3 and 5 above. Migrations run when the api container starts.
2. Watch the logs while it starts: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f api worker`

**Roll back:** check out the previous commit and repeat step 1. Migrations are not rolled back
automatically; a migration that drops or changes data needs its own plan before it ships.

## Backups

`sh infrastructure/scripts/backup-db.sh` writes a compressed `pg_dump` to `backups/` and keeps the last 14.
On a server, run it daily from cron and copy `backups/` off the machine. Restore into an empty database:

```bash
gunzip -c backups/figurepose-<date>.sql.gz | docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres psql -U figurepose figurepose
```

Photos live in the `storage_data` volume. In production, use a managed S3 bucket instead
(`S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION` and the keys); the backend only speaks S3, so nothing else changes.

## Logs and request IDs

Every API response has an `X-Request-Id` header. The same ID is in nginx's access log line and in every
Laravel log line of that request, so a user's report can be traced:
`docker compose -f docker-compose.prod.yml --env-file .env.prod logs api web | grep <request id>`

## Still to do before real users

- TLS: put Caddy or a host nginx with Let's Encrypt in front of `web`, and set `APP_URL` to `https://…`.
- A firewall that allows only 80/443 (and SSH).
- Off-site copies of the database dumps and photos.
- Uptime monitoring on `/api/v1/health`.
- AI visuals: off by default. To turn them on, set `GENERATION_ENABLED=true`, `AI_GENERATION_PROVIDER=openai`, `GENERATION_PROVIDER_NAME=OpenAI` and `OPENAI_API_KEY` in `.env.prod`, and set a spending limit in the OpenAI dashboard first. Check OpenAI's current data-use terms for API images and say what they are in the privacy notice.
