#!/bin/sh
# Builds the Flutter web app for the production-like stack, which serves it and the API from one origin.
#   sh infrastructure/scripts/build-web.sh
# Git Bash on Windows rewrites arguments that look like paths ("/api/v1" becomes "C:/Program Files/Git/api/v1"),
# so path conversion is switched off here.
set -e
cd "$(dirname "$0")/../../mobile"
MSYS_NO_PATHCONV=1 flutter build web --release --dart-define=API_BASE_URL=/api/v1
grep -q '"/api/v1"' build/web/main.dart.js || grep -q '/api/v1' build/web/main.dart.js
if grep -q 'Program Files' build/web/main.dart.js; then
  echo "build-web: API_BASE_URL was rewritten into a Windows path; the build is wrong" >&2
  exit 1
fi
echo "Built mobile/build/web with API at /api/v1"
