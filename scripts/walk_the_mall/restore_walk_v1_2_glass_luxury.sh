#!/usr/bin/env bash

set -e

cd /workspaces/majicmall
source .venv/bin/activate

SOURCE="backups/walk_the_mall/versions/walk_v1_2_glass_luxury_master.html"
TARGET="core/templates/mall/walk_world.html"

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: Saved V1.2 master was not found:"
  echo "$SOURCE"
  exit 1
fi

cp "$TARGET" \
  "backups/walk_the_mall/versions/walk_before_restore_$(date +%Y%m%d_%H%M%S).html"

cp "$SOURCE" "$TARGET"

python manage.py check
python manage.py collectstatic --noinput

echo
echo "Walk the Mall V1.2 Glass Luxury restored."
