# HD Guru Frontend

Next.js 15 (App Router) + Tailwind v4 progressive web app for HD Guru.
Installable PWA, offline fallback, dynamic branding from the backend admin
panel. Deployed on **Vercel** (see `vercel.json` at the repo root and
`SETUP.md`).

## Requirements

- Node.js 20+
- A running HD Guru backend for live mode (see `../backend/README.md`)

## Setup

```bash
npm install
copy .env.example .env.local   # then set NEXT_PUBLIC_API_URL
npm run dev                    # http://localhost:3000
```

## Environment variables

Only `NEXT_PUBLIC_*` variables reach the browser. **Never** put secrets here
(Meta tokens, R2 keys, JWT secrets belong to the backend).

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Public API base URL (e.g. `http://localhost:8000` local, `https://hd-guru-api.onrender.com` in prod). Without it the app runs in demo mode with mock data. |
| `NEXT_PUBLIC_APP_URL` | Public origin of this frontend (default `https://hdguru.vercel.app`). Used for SEO metadata, sitemap/robots and PWA manifest icon URLs. |

## Scripts

```bash
npm run dev        # development server
npm run build      # production build (regenerates public/sw.js via next-pwa)
npm start          # serve the production build
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
```

## How it talks to the backend

`services/api.ts` resolves `API_BASE_URL` from `NEXT_PUBLIC_API_URL` once.
All API calls go through it: upload (`POST /api/v1/uploads`), job status
polling, result/download/thumbnail URLs, public branding
(`GET /api/v1/settings/public`), ads config, analytics events and admin APIs.
If the backend is unreachable the app falls back to demo/mock mode.

## PWA

- Manifest: `app/manifest.ts` — generated per-request so **Admin → Settings**
  branding (app name, description, theme color) is reflected at install time.
- Service worker: next-pwa config in `next.config.mjs` (precache, runtime
  caching for static assets/icons/images/fonts, navigation fallback to
  `/offline`).
- Icons: `public/icon-192.png`, `public/icon-512.png` (any + maskable),
  `public/apple-touch-icon.png`; favicon `app/favicon.ico`.
- Run `npm run build` after PWA changes so `public/sw.js` is regenerated.

## Branding

The public app fetches branding from `GET /api/v1/settings/public`
(`services/branding.ts`, cached ~5 min) and applies app name, logo, theme
color and description to the document and manifest. If branding is unset it
uses the compiled HD Guru defaults and never breaks. One source of truth: the
backend Setting rows edited in **Admin → Settings**. PWA icons/favicon are
build-time assets (documented limitation — see `SETUP.md` §34).

## Deploy on Vercel

Import the repository. The committed `vercel.json` sets
`rootDirectory: frontend` and `framework: nextjs`. Set
`NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_APP_URL` in Project Settings →
Environment, then Deploy. HTTPS is automatic.
