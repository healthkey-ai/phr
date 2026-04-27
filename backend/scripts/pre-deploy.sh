#!/usr/bin/env sh
#
# Runs once per deploy before the web service accepts traffic.
#
# Render's `preDeployCommand` hook — see render.yaml. Safe to re-run
# (migrations and loaddata are idempotent). Any non-zero exit aborts
# the deploy, so a broken migration or missing fixture fails fast.
#
set -eu

echo "[pre-deploy] running database migrations"
python manage.py migrate --noinput

echo "[pre-deploy] collecting static files"
python manage.py collectstatic --noinput

echo "[pre-deploy] done"
