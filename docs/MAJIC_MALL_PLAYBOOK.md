# Majic Mall Playbook

## Adding a New Zone

### When to use this
Use this when adding a permanent zone to the platform.

### Steps

1. Open:
merchant/management/commands/seed_zones.py

2. Add your new zone to the list:

zones = [
    "Fashion Zone",
    "Tech Zone",
    "Food Court",
    "Theater Zone",
    "Music Zone",
    "Business Services Zone",
    "ATL's Hottest Zone",  # example
]

3. Save file

4. Commit and push:

git add merchant/management/commands/seed_zones.py
git commit -m "Add new zone"
git push

5. Run on Render:

python manage.py seed_zones

### Notes
- Safe to run multiple times (uses get_or_create)
- Will NOT duplicate zones
- This is the source of truth for platform zones

---

## Deploying to Render (Django + Docker)

### Overview
Majic Mall is deployed on Render using Docker and PostgreSQL.

---

### Standard Deploy Flow

1. Make code changes locally (Codespaces)

2. Commit and push:

git add .
git commit -m "Describe your change"
git push

3. Render automatically:
- Builds Docker image
- Runs pre-deploy command (migrations)
- Starts the app

---

### Important Configuration

#### Database
- Uses PostgreSQL in production
- Controlled by `DATABASE_URL` environment variable
- Falls back to SQLite locally if not set

#### Entrypoint (entrypoint.sh)

Production startup should NOT run migrations.

Correct version:

```sh
#!/usr/bin/env sh
set -e

python manage.py collectstatic --noinput

exec gunicorn majicmall.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --log-level info \
  --access-logfile - \
  --error-logfile -