#!/usr/bin/env sh
set -e

python manage.py migrate --noinput
python manage.py seed_zones
