#!/bin/sh
# Production entrypoint: wait for the database, prepare the app once (API container only), then run CMD.
set -e

until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" >/dev/null 2>&1; do
  echo "waiting for postgres..."; sleep 1
done

# Cached config and routes: env vars are read here, once, so they must all be set in the container.
php artisan config:cache
php artisan route:cache

if [ "${RUN_SETUP:-false}" = "true" ]; then
  php artisan migrate --force
  # Figure types and the pose catalog. Safe to repeat: both seeders update in place.
  php artisan db:seed --force
  for i in 1 2 3 4 5 6 7 8 9 10; do
    php artisan figurepose:ensure-bucket && break
    echo "waiting for object storage..."; sleep 2
  done
fi

# config:cache ran as root; PHP-FPM workers run as www-data and must be able to read and write.
chown -R www-data:www-data storage bootstrap/cache

exec "$@"
