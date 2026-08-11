# HD Guru Backend

FastAPI + SQLAlchemy + Celery API and media processing engine for HD Guru.

> **Production deployment** → see **[SETUP.md](../SETUP.md)**. The repo root
> ships a **Render Blueprint** (`render.yaml`) + production image
> (`render.Dockerfile`, FFmpeg installed, migrations run on boot) that
> provisions PostgreSQL, Redis, the API web service, the Celery worker and
> beat. This README covers local development and the internals.

## Requirements

- Python 3.12+ (developed on 3.14)
- Redis (Celery broker/result backend)
- PostgreSQL (default) or SQLite for local dev (`DATABASE_URL`)
- FFmpeg + ffprobe on PATH (video pipeline only; the image pipeline needs none)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
copy .env.example .env            # then edit DATABASE_URL / JWT_SECRET_KEY
alembic upgrade head
```

### Storage backends

Media is stored through a single `BaseStorage` abstraction behind
`STORAGE_DRIVER`:

- **`local`** (default) — files under `STORAGE_DIR`, artifacts under
  `{upload_public_id}/{media_public_id}/optimized` and `…/thumbnails`.
- **`s3`** — S3-compatible object storage (Cloudflare R2 / AWS S3 / MinIO) via
  boto3. Objects are organized by public media ID (never the original
  filename): `media/{original|processed|thumbnails}/{YYYY}/{MM}/{public_id}.ext`.

Set the `S3_*` variables in `.env` (see `.env.example`) and choose how clients
receive media URLs with `MEDIA_URL_MODE`:

- `public` — direct URL built from `S3_PUBLIC_BASE_URL` (public bucket / CDN).
- `signed` — short-lived pre-signed URL (`MEDIA_SIGNED_URL_EXPIRES` seconds).

Local storage always falls back to the app's own `/uploads/{id}/file` route.
On the S3 driver the same endpoint responds with a redirect to the media URL.
Download counts still increment on `/file` regardless of driver.

Expired uploads are deleted by the `uploads.cleanup_expired` beat task (runs
hourly) and once at startup; objects are removed through the storage driver, so
cleanup works for cloud buckets too. Rows are only removed after their objects
are gone.

## Run

```bash
# API
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Worker (asynchronous processing; without it uploads stay queued)
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
```

Or use Docker Compose (Postgres + Redis + API + worker, FFmpeg included):

```bash
docker compose up --build
```

## Tests

```bash
.venv\Scripts\python -m pytest
```

Tests run against SQLite with the Celery worker in eager mode (the real
Pillow pipeline runs inline), so they need no Redis/Postgres/FFmpeg.

## Configuration management

Runtime configuration is split between **environment variables** (infrastructure,
startup configuration, and secrets — set on Render / in `.env`, a change needs a
redeploy) and the **database-backed settings** edited from the admin dashboard
(no redeploy needed).

| Setting | Source of truth | Change without deploy? | Secret? |
| --- | --- | --- | --- |
| `ads.enabled` / `ads.default_provider` / `ads.default_placement_behavior` | DB (`settings`), Admin → Ads | Yes | No |
| `analytics.enabled` / `analytics.retention_days` | DB (`settings`), Admin → Analytics | Yes | No |
| `upload.ttl_hours`, `upload.max_*`, `upload.allowed_mime_types` | DB (`settings`), Admin → Settings | Yes | No |
| `rate_limit.enabled` | DB (`settings`), Admin → Settings | Yes | No |
| `watermark.enabled` | DB (`settings`), Admin → Settings / Watermark | Yes | No |
| WhatsApp operational config (enabled, phone number, tokens…) | DB (`whatsapp_settings`), Admin → WhatsApp | Yes | Tokens masked, never shown |
| `DATABASE_URL`, `REDIS_URL`, `CELERY_*` | Render environment | No | Yes |
| `JWT_SECRET_KEY` | Render environment | No | Yes |
| `S3_*` (R2 credentials, bucket) | Render environment | No | Yes |
| SMTP credentials | Render environment | No | Yes |

The env vars for DB-backed keys (`DEFAULT_UPLOAD_TTL_HOURS`,
`RATE_LIMIT_ENABLED`, `WATERMARK_ENABLED`, `ADS_ENABLED`, `ANALYTICS_ENABLED`,
`WHATSAPP_*`, …) act only as first-run fallbacks: they are read when no
DB row exists yet, and a DB value always wins afterwards.

## API

All routes are under `/api/v1`.

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/uploads` | Upload 1–5 files → `{"success": true, "jobs": [{"id", "status"}]}` |
| `GET` | `/uploads/{id}/status` | Per-file status: `queued/analyzing/enhancing/watermarking/compressing/storing/completed/failed/expired` |
| `GET` | `/uploads/{id}` | Batch summary, or a single media file by public ID |
| `GET` | `/uploads/{id}/file` | Download processed file (increments `download_count`) |
| `GET` | `/uploads/{id}/thumbnail` | Thumbnail (JPEG) of processed file |
| `DELETE` | `/uploads/{id}` | Delete batch or single file by public ID |
| `GET` | `/uploads/{id}` | Also returns `whatsapp_url` (a ready wa.me link) when WhatsApp is enabled |
| `GET` | `/public/whatsapp` | Public availability: enabled, phone number, message template |
| `GET` | `/whatsapp/webhook` | Meta webhook verification handshake (echoes the challenge) |
| `POST` | `/whatsapp/webhook` | Meta webhook receiver (signature-checked, acknowledged immediately) |
| `GET` | `/whatsapp/config` | Effective configuration with secrets masked (admin) |
| `PUT` | `/whatsapp/config` | Update the persisted WhatsApp settings row (admin) |
| `POST` | `/whatsapp/config/test` | Test the Meta connection against the phone number ID (admin) |
| `GET` | `/whatsapp/webhook/status` | Webhook health: last received/processed/failed events (admin) |

Public IDs are 16 random characters (`A–Z`, `a–z`, `0–9`). File/thumbnail
downloads and single-file GET/DELETE are public by ID; the batch GET enforces
owner/admin access for the full view.

## WhatsApp delivery

When WhatsApp is enabled (DB `whatsapp_settings.enabled`, toggled in
**Admin → WhatsApp → Configuration**, no redeploy) the frontend shows a "Open
WhatsApp" button built
from a backend-generated `wa.me` link (`whatsapp_url`). It pre-fills
`Send HD for <16-char public ID>`. Messages sent to the business number are
received by the webhook and the processed file is delivered back through the
Meta Graph API.

Flow: user taps the WhatsApp button → sends `Send HD for <ID>` → Meta calls
`POST /api/v1/whatsapp/webhook` → signature is verified with
`X-Hub-Signature-256` + `WHATSAPP_APP_SECRET` → the request is acknowledged
immediately and each event is enqueued → the `whatsapp.process_event` Celery
task parses the ID, looks the media up (exists? expired? completed? processed
file present?), and replies with the processed file (image/video/document by
MIME type) or a friendly message.

- Idempotency: Meta's message ID is stored on `whatsapp_messages.meta_message_id`
  (unique); duplicate deliveries are acknowledged and never re-sent.
- Delivery status webhooks (`sent/delivered/read/failed`) are recorded on
  `whatsapp_message_statuses` and update the outbound message.
- Rate limiting: a per-process sliding-window backstop
  (`WHATSAPP_MAX_SENDS_PER_MINUTE`) plus bounded Celery retries for transient
  Graph errors (429, 5xx, timeouts). Permanent errors fail fast and are stored
  on the event row.
- Media is sent by URL: for `s3` storage via `MEDIA_URL_MODE=public/signed`;
  for local storage via `{APP_PUBLIC_BASE_URL}/api/v1/uploads/{id}/file`.
  Files are never buffered in worker memory.

### Setting up Meta

1. Create an app in the Meta App Dashboard (type *Business*), add the
   **WhatsApp** product, and connect your business phone number.
2. From the WhatsApp *API setup* tab copy the **Phone number ID** (and the
   business phone number). Generate a system-user token with the
   `whatsapp_business_messaging` and `whatsapp_business_management`
   permissions — this is the **access token**.
3. In the app's *Webhooks* section add the **WhatsApp** webhook with callback
   URL `https://<your-host>/api/v1/whatsapp/webhook` and a **verify token** you
   choose. When Meta calls back, the API
   echoes the `hub.challenge` and Meta registers the webhook. Then *subscribe*
   to the `messages` field.
4. Copy the **App secret** from the dashboard.
5. Enter all of these in **Admin → WhatsApp → Configuration** (stored in the
   DB, effective without a redeploy) together with `WHATSAPP_PHONE_NUMBER` and
   `APP_PUBLIC_BASE_URL` (or `S3_*` public/signed URLs) — the env fallbacks
   `WHATSAPP_*` are only used before a DB row exists.

Verify with `POST /api/v1/whatsapp/config/test` (admin) — it checks the token
and phone number ID against the Graph API without exposing credentials.

### Testing the webhook locally

No Meta app is required to exercise the flow. With the API running, generate a
signature for a sample payload and POST it to the webhook:

```bash
# replace SECRET and the payload body; the endpoint only needs the header
curl -X POST http://localhost:8000/api/v1/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$(python -c "import hmac,hashlib,sys;print(hmac.new(b'SECRET', open('body.json','rb').read(), hashlib.sha256).hexdigest())")" \
  --data-binary @body.json
```

`body.json` is a normal Meta `messages` payload (see the `messages` field
shape in the Graph docs). The API answers `200` and the event lands in the DB
where the worker processes it. Without a configured token the events are stored
and marked `ignored`; with a token they are attempted against the real Graph
API, so in a local sandbox use the env-var-less flow above to verify
acknowledgement, signature checking and event persistence.

## Pipeline

`POST /uploads` → validation (count/MIME/magic/size) → streaming to storage →
per-file jobs → Celery worker runs `queued → analyzing → enhancing →
watermarking → compressing → storing → completed` (or `failed`), committing each
stage so `/status` reports real progress. Processed artifacts are stored under
`{upload_public_id}/{media_public_id}/optimized` and `…/thumbnails`, so one
`DELETE /uploads/{batch_id}` removes everything.

- **Images** (Pillow): EXIF transpose → RGB → strip metadata → max 2048px edge →
  subtle enhance (contrast 1.05 + unsharp mask) → DB watermark → progressive
  JPEG q 90–95 with step-down (floor q 70) until <5MB → 320px thumbnail.
- **Videos** (FFmpeg): `ffprobe` → rotate metadata → preserve aspect (caps:
  portrait 1080×1920 / landscape 1920×1080 / square 1080×1080, never upscale) →
  H.264/AAC, `yuv420p`, `+faststart` → CRF re-encode loop until <16MB or the
  `MIN_VIDEO_QUALITY` floor (bounded attempts) → thumbnail from a representative
  frame.
- **Watermark** comes from the active `watermarks` DB row (position/opacity/size/
  enabled, 9 positions) and is rendered to a standalone RGBA PNG with opacity
  baked in, so Pillow and FFmpeg composite it identically. The applied settings
  are recorded in `ProcessedMedia.watermark_ref`.

## Layout

```
app/
├── api/v1/endpoints/uploads.py   # upload / status / get / delete / file / thumbnail
├── api/v1/endpoints/whatsapp.py  # webhook + config + public endpoints
├── core/                         # config, database, storage, exceptions, bootstrap
├── models/                       # SQLAlchemy models (Upload, MediaFile, ProcessedMedia, …)
├── schemas/                      # Pydantic response/request schemas
├── services/
│   ├── processing/               # image_processor.py (Pillow), video_processor.py (FFmpeg)
│   ├── watermark_service.py      # DB-driven watermark rendering + placement
│   ├── upload_service.py         # upload/delete orchestration
│   ├── whatsapp/                 # errors, config, webhook, client, messages, media, service
│   └── …
└── workers/tasks.py              # Celery pipeline + whatsapp.process_event (queue "uploads")
alembic/                          # migrations (0001 base, 0002 media pipeline, 0003 storage, 0004 whatsapp)
tests/                            # pytest suite (SQLite + eager worker)
```
