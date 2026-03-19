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