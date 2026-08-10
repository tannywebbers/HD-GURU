# HD Guru

Transform photos and videos into WhatsApp-friendly HD quality. Upload up to 5
files, the backend enhances, watermarks and compresses them (images via Pillow,
videos via FFmpeg), and the frontend guides you through processing to download.

> **Production deployment** → read **[SETUP.md](SETUP.md)** first. It covers
> Vercel (frontend), Render (backend + worker + beat + DB + Redis), Cloudflare
> R2 storage, the Meta WhatsApp Business webhook, PWA/branding, security,
> troubleshooting and the full end-to-end test plan. This README covers local
> development.

## Repository structure

```
HD-GURU/
├── backend/    # FastAPI + SQLAlchemy + Celery API and media processing engine
└── frontend/   # Next.js 15 + Tailwind v4 client
```

## Backend

### Requirements
- Python 3.12+ (developed on 3.14)
- Redis (Celery broker/result backend)
- PostgreSQL (default), or switch `DATABASE_URL` to SQLite for local dev
- FFmpeg + ffprobe on PATH (video pipeline)

### Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
copy .env.example .env            # then edit DATABASE_URL / JWT_SECRET_KEY
alembic upgrade head
```

### Run

```bash
# API
uvicorn app.main:app --reload

# Worker (processes uploads asynchronously)
celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
```

Or use Docker Compose (Postgres + Redis + API + worker, FFmpeg included):

```bash
docker compose up --build
```

API docs: http://localhost:8000/docs

### Media pipeline
`POST /api/v1/uploads` → per-file jobs (`{"success": true, "jobs": [{"id": "…", "status": "queued"}]}`) →
Celery worker runs `queued → analyzing → enhancing → watermarking → compressing →
storing → completed` (or `failed`) → `GET /api/v1/uploads/{id}/status` polls progress.

- **Images** (JPEG/PNG/WEBP, via Pillow): EXIF orientation fix, metadata removal,
  resize to max 2048px, subtle sharpen/contrast, progressive JPEG (q 90–95),
  target <5MB with quality step-down.
- **Videos** (MP4/MOV/MKV/AVI/WEBM, via FFmpeg): probe → preserve aspect ratio
  (caps: portrait 1080×1920, landscape 1920×1080, square 1080×1080) → H.264/AAC,
  yuv420p, faststart → CRF re-encode loop targeting <16MB with a quality floor.
- **Watermark** is applied from the active `watermarks` DB record (position,
  opacity, size, enabled; 9 positions). Default text watermark is seeded on
  startup if none exists.
- Expired uploads are removed by the `uploads.cleanup_expired` beat task and at
  startup; objects are deleted through the storage driver (works for local and
  cloud buckets). Rows are removed only after their objects are gone.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Production build:

```bash
npm run build
npm start
```

The frontend talks to the backend through `frontend/services/api.ts`. Set
`NEXT_PUBLIC_API_URL` (e.g. `http://localhost:8000`) to enable live backend
calls; without it the app runs in demo mode with mock responses.

## Environment variables (backend)

See `backend/.env.example` for the full list. Key ones:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | (required) | SQLAlchemy database URL |
| `REDIS_URL` / `CELERY_BROKER_URL` | `redis://localhost:6379/0` / `/1` | Redis + Celery |
| `STORAGE_DRIVER` | `local` | `local` or `s3` (S3-compatible object storage) |
| `S3_ENDPOINT_URL` | — | S3 API endpoint (R2/AWS/MinIO) when `STORAGE_DRIVER=s3` |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | — | Storage credentials (never exposed/logged) |
| `S3_BUCKET_NAME` / `S3_REGION` | — / `auto` | Bucket + region (`auto` for R2) |
| `S3_PUBLIC_BASE_URL` | — | Public/CDN base URL for `MEDIA_URL_MODE=public` |
| `MEDIA_URL_MODE` | `public` | `public` (direct URL) or `signed` (pre-signed URL) |
| `MEDIA_SIGNED_URL_EXPIRES` | `3600` | Signed URL lifetime in seconds |
| `MAX_UPLOAD_FILES` | `5` | Max files per upload |
| `MAX_IMAGE_OUTPUT_SIZE` | `5` | Target max image output size (MB) |
| `MAX_VIDEO_OUTPUT_SIZE` | `16` | Target max video output size (MB) |
| `MAX_VIDEO_WIDTH` / `MAX_VIDEO_HEIGHT` | `1920` / `1080` | Video dimension caps |
| `MIN_VIDEO_QUALITY` | `28` | Video CRF floor (lower = higher quality) |
| `MEDIA_EXPIRATION_DAYS` | `3` | Media file expiry in days |
| `WATERMARK_ENABLED` | `true` | Master watermark toggle |
| `WHATSAPP_ENABLED` | `false` | Enable WhatsApp click-to-chat delivery |
| `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` | — | Meta Graph API token + phone number ID |
| `WHATSAPP_PHONE_NUMBER` | — | Business number (E.164, used for wa.me links) |
| `WHATSAPP_VERIFY_TOKEN` / `WHATSAPP_APP_SECRET` | — | Webhook verification token + signature secret |
| `WHATSAPP_GRAPH_API_VERSION` | `v22.0` | Graph API version for messages/media endpoints |
| `APP_PUBLIC_BASE_URL` | — | Public API base URL (local-storage media links for WhatsApp) |
| `ADS_ENABLED` | `false` | Master toggle for the public ad-serving system |
| `ADS_DEFAULT_PROVIDER` | `""` | Provider name used by placements with no explicit provider |
| `ADS_DEFAULT_PLACEMENT_BEHAVIOR` | `lazy` | `lazy` (load near viewport) or `eager` (load at mount) |
| `ANALYTICS_ENABLED` | `true` | Master toggle for traffic analytics |
| `ANALYTICS_RETENTION_DAYS` | `90` | Raw event retention window (purged by admin or beat task) |
| `ANALYTICS_EVENTS_PER_MINUTE` | `120` | Analytics ingest budget per client (hashed IP) |
| `AD_EVENTS_PER_MINUTE` | `60` | Ad event ingest budget per client (hashed IP) |

## WhatsApp delivery

When enabled, each completed file returns a backend-built `wa.me` link. The
user sends `Send HD for <16-char ID>` and the processed file is delivered back
via the Meta WhatsApp Cloud API. See `backend/README.md` → *WhatsApp delivery*
for the Meta app setup, the `whatsapp.process_event` worker flow, idempotency
and rate limiting, plus how to test the webhook locally without a Meta app.

## Production deployment (Phase 8)

- **Vercel**: import the repo (or use the committed `vercel.json`, which sets
  root directory `frontend`). Set `NEXT_PUBLIC_API_URL` and
  `NEXT_PUBLIC_APP_URL` (see `frontend/.env.example`).
- **Render**: import the repo as a **Blueprint** — the committed
  `render.yaml` provisions PostgreSQL + Redis + the FastAPI web service +
  Celery worker + beat, and `render.Dockerfile` installs FFmpeg and runs
  `alembic upgrade head` on boot. Fill the `sync: false` secrets (S3/WhatsApp/
  admin/CORS) after the first deploy.
- **Storage**: `STORAGE_DRIVER=s3` with Cloudflare R2 (`S3_ENDPOINT_URL`,
  `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION=auto`).
- **WhatsApp**: register `POST /api/v1/whatsapp/webhook` in the Meta app and
  set the WhatsApp env vars.

Full step-by-step guide, troubleshooting and the production checklist live in
**[SETUP.md](SETUP.md)**.

## Ads & analytics (Phase 7)

The app ships with a privacy-conscious advertising system and traffic
analytics, both fully managed from the admin dashboard (**Ads** and
**Analytics** in the sidebar).

### Ads

- **Public config endpoint** `GET /api/v1/ads/config` — returns only safe,
  public data (placement layout + assigned provider ad units). Provider
  `api_key`s and credentials are never included, disabled placements/providers
  are not served, and custom script placements render into a sandboxed
  `iframe` (`sandbox="allow-scripts"`).
- **10 built-in providers** are seeded: Google AdSense, Adsterra, PropellerAds,
  Monetag, Media.net, Ezoic, Setupad, HilltopAds, RevContent and Taboola. Add
  more in `Admin → Ads → Providers` (types: `banner`, `native`, `pop`,
  `custom_script`).
- **10 placements** are seeded. 8 are wired into the public frontend: landing
  top/bottom, upload bottom, processing bottom, countdown bottom, result
  top/bottom and a global footer slot (`landing_middle` and `countdown_top`
  are available for new pages). Assign multiple providers per placement with
  per-provider frequency caps (`every_view` / `interval` / `daily` / `session`)
  and priority ordering (`Admin → Ads → Placements`).
- Ad components lazy-load on scroll (IntersectionObserver), expose analytics
  hooks (`ad_impression`, `ad_click`, `ad_load_failure`) and never block the
  main app. Turn the whole system off with `ADS_ENABLED=false` (default).

### Analytics

- Server-side, cookie-free tracking: `page_view`, `upload_started`,
  `upload_completed`, `processing_completed`, `get_hd_clicked`,
  `whatsapp_opened`, `whatsapp_message_received`, `media_delivered`,
  `upload_failed` and `processing_failed`. Bots are filtered, sessions counted
  once per day, referrers are categorised, and device/browser/OS are parsed
  from the UA string.
- Admin surfaces (`/api/v1/admin/analytics/*`): 30-day overview,
  daily timeseries, top pages, device/browser/OS breakdowns, referrer
  categories and a filterable raw event log. Raw events are purged after
  `ANALYTICS_RETENTION_DAYS` (90) — manually via the Analytics page's
  *Run retention* button or by the daily beat task.
- **Funnel checks**: overview cards show uploads → uploads completed →
  processing rate → GET HD clicks → WhatsApp opens/requests → media deliveries,
  so you can spot where users drop off.

### First-run setup

1. `ADS_ENABLED=true` (and restart the API) so the public `/ads/config` serves data.
2. Log into the admin dashboard → **Ads** → **Providers** → *Add provider* with
   your real network credentials (e.g. AdSense publisher ID).
3. **Placements** → for each placement pick the provider, set its frequency cap
   and priority, and enable it.
4. Watch the funnel and ad performance on **Analytics**.
