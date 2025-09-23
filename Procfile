web: python3 -m gunicorn majicmall.wsgi:application --bind 0.0.0.0:$PORT
release: python3 manage.py migrate --noinput && python3 manage.py collectstatic --noinput
