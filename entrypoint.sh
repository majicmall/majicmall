#!/usr/bin/env sh
set -e

python manage.py collectstatic --noinput

exec gunicorn majicmall.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --log-level info \
  --access-logfile - \
  --error-logfile -
