FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# entrypoint will run migrations + collectstatic, then start gunicorn
RUN chmod +x ./entrypoint.sh

ENV PORT=8000
EXPOSE 8000
CMD ["./entrypoint.sh"]
