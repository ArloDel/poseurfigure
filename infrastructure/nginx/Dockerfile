# nginx with the web app and catalog photos baked in. Build from the repository root:
#   flutter build web (see README "Production-like stack"), then docker compose -f docker-compose.prod.yml build
FROM nginx@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de

COPY infrastructure/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY infrastructure/nginx/security-headers.inc /etc/nginx/snippets/security-headers.inc
COPY backend/public/catalog /srv/catalog
COPY mobile/build/web /srv/web
