# Render production image for HD Guru.
#
# This Dockerfile mirrors backend/Dockerfile but is built from the repository
# ROOT (Render's docker build context is the repo root). It copies only the
# backend/ directory into the image. FFmpeg is installed here - do NOT assume
# it exists on the host. The entrypoint runs migrations before starting the
# API; the Celery worker/beat services override the CMD via render.yaml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# FFmpeg is required by the video processing pipeline.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ .

RUN mkdir -p /app/storage

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
