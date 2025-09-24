#!/usr/bin/env sh
set -eu

# Safety defaults (Render will set real values in env)
: "${DJANGO_SECRET_KEY:=CHANGE_ME}"
: "${DJANGO_DEBUG:=False}"

python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput

exec gunicorn majicmall.wsgi:application --bind 0.0.0.0:${PORT:-8000}
