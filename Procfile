web: /app/.venv/bin/python -m gunicorn majicmall.wsgi:application --bind 0.0.0.0:$PORT
release: /app/.venv/bin/python manage.py migrate --noinput && /app/.venv/bin/python manage.py collectstatic --noinput

