#!/bin/sh
# Dumps the production-like stack's database to backups/figurepose-<UTC time>.sql.gz and keeps the newest 14.
#   sh infrastructure/scripts/backup-db.sh
# On a server, run it daily from cron and copy backups/ to another machine. See docs/DEPLOY.md.
set -e
cd "$(dirname "$0")/../.."
mkdir -p backups
out="backups/figurepose-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres \
  pg_dump -U figurepose --no-owner --clean --if-exists figurepose | gzip > "$out.part"
# Only a complete dump gets the real name, so a failed run never looks like a backup.
mv "$out.part" "$out"
echo "Wrote $out ($(wc -c < "$out") bytes)"

ls -1t backups/figurepose-*.sql.gz | tail -n +15 | while read -r old; do rm -f "$old"; done
