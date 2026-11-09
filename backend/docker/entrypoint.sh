#!/bin/sh
# Dev entrypoint: wait for dependencies, prepare the app, then run CMD.
set -e

if [ ! -d vendor ]; then
  composer install --no-interaction --prefer-dist
fi

until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" >/dev/null 2>&1; do
  echo "waiting for postgres..."; sleep 1
done

# Only the API container prepares the database and bucket; the worker just waits for it.
if [ "${RUN_SETUP:-false}" = "true" ]; then
  php artisan migrate --force
  php artisan db:seed --force
  for i in 1 2 3 4 5 6 7 8 9 10; do
    php artisan figurepose:ensure-bucket && break
    echo "waiting for object storage..."; sleep 2
  done
fi

exec "$@"
