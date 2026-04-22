# QR Service

A full-stack Django application for generating QR codes, tracking scans, and viewing analytics. Built with Django REST Framework on the backend and vanilla HTML/CSS/JavaScript on the frontend.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Testing](#testing)
- [API Endpoints](#api-endpoints)
- [Authentication Flow](#authentication-flow)
- [Security](#security)
- [Frontend Design System](#frontend-design-system)
- [How the Frontend Talks to the Backend](#how-the-frontend-talks-to-the-backend)
- [Claude Code Integration](#claude-code-integration)
- [Troubleshooting](#troubleshooting)

---

## Overview

QR Service lets authenticated users:

1. Generate QR codes that redirect to any URL they choose.
2. Track every scan (timestamp, IP, user agent, referrer).
3. View analytics and manage their codes from a dashboard.
4. Secure their account with email verification and TOTP-based 2FA.

The API is fully documented via Swagger UI at `/docs/`, and the frontend is rendered directly by Django templates (no SPA build step required).

---

## Features

### Core
- **QR code generation** — turn any URL into a scannable PNG.
- **Scan tracking** — every time a QR is scanned, the redirect endpoint records a `Scan` row with metadata.
- **Analytics dashboard** — per-code totals, recent activity, and per-user aggregates.
- **Per-user ownership** — users can only see and manage their own codes.

### Authentication & Security
- **JWT authentication** (SimpleJWT) with access + refresh tokens and token rotation/blacklisting.
- **Mandatory email verification** via django-allauth (console backend in dev, SMTP in prod).
- **Two-factor authentication** (TOTP) with Google Authenticator / Authy / 1Password compatibility.
- **Rate limiting** via DRF throttling (30/min anon, 100/min user).
- **URL scheme allowlist** on QR payloads (only `http`/`https` accepted).
- **Path traversal protection** on media file serving.
- **XSS-safe templates** using `textContent` / `escapeHtml()` in all client-side rendering.

### Quality

- **Automated test suite** — 45 tests covering QR CRUD, ownership enforcement, scheme allowlist, path traversal, JWT login, 2FA setup/verify/disable, and analytics scoping.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Web framework | Django 6.0 |
| API framework | Django REST Framework |
| Auth | djangorestframework-simplejwt, django-allauth, django-otp |
| Database | PostgreSQL (via psycopg2-binary, dj-database-url) |
| QR generation | qrcode, pillow |
| API docs | drf-spectacular (Swagger UI) |
| Frontend | Django templates, vanilla JS, DM Sans font |
| Deployment | Procfile-based (Heroku / Render / Railway compatible) |

---

## Project Structure

```
qr_service/
├── config/                    Project-level Django configuration
│   ├── settings/
│   │   ├── base.py            Shared settings (apps, middleware, REST, JWT, allauth)
│   │   ├── development.py     Dev overrides (.env loading, SECRET_KEY validation)
│   │   └── production.py      Prod overrides (HSTS, SSL redirect, STORAGES)
│   ├── urls.py                Root URL router (frontend + API + admin + allauth)
│   ├── frontend_views.py      Views that render the HTML templates
│   └── wsgi.py / asgi.py
├── qr/                        QR code generation & management
│   ├── models.py              QRCode model
│   ├── views.py               CRUD + redirect + image serving endpoints
│   ├── services/qr_service.py PNG generation with scheme allowlist
│   └── urls.py
├── analytics/                 Scan tracking
│   ├── models.py              Scan model
│   ├── views.py               Analytics endpoints
│   └── urls.py
├── users/                     Authentication
│   ├── views.py               Register, login (me), 2FA setup/confirm/disable/verify
│   ├── serializers.py
│   └── urls.py
├── templates/                 Server-rendered HTML
│   ├── base.html              Layout, nav, global CSS variables, helper JS
│   ├── landing.html           Marketing page
│   ├── login.html             Login form + 2FA challenge
│   ├── register.html          Signup form + email verification notice
│   ├── dashboard.html         Code list, create form, modal
│   └── settings.html          Profile, 2FA setup, danger zone
├── storage/                   Generated QR PNGs (MEDIA_ROOT)
├── staticfiles/               Collected static assets
├── manage.py
├── Procfile                   Deployment entrypoint (gunicorn)
├── requirements.txt
├── CLAUDE.md                  Instructions for Claude Code
└── .claude/settings.json      Claude Code permission rules (denies .env access)
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL running locally (or a `DATABASE_URL`)
- pip + virtualenv

### Install

```bash
git clone <repo-url>
cd qr_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure environment

Create a `.env` file in the project root (never commit this file — it is already gitignored and blocked from Claude Code):

```bash
DJANGO_SECRET_KEY=your-50-char-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=qr_service
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Initialize the database

```bash
createdb qr_service
python manage.py migrate
python manage.py createsuperuser
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SECRET_KEY` | yes | Django secret key. Validated on dev and prod startup. |
| `DJANGO_DEBUG` | no | `True` in development, `False` in production. Default: `False`. |
| `DJANGO_ALLOWED_HOSTS` | prod | Comma-separated list of hosts. |
| `DATABASE_URL` | alt | Postgres URL; takes precedence over the `DB_*` variables. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | alt | Discrete Postgres credentials. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | prod | SMTP config for verification emails (dev uses console). |

---

## Running the App

```bash
# Development (http://localhost:8000)
python manage.py runserver

# Tests
python manage.py test

# Create migrations after model changes
python manage.py makemigrations
python manage.py migrate

# Collect static files (prod)
python manage.py collectstatic --noinput
```

URLs once running:

| URL | What it serves |
|-----|----------------|
| `/` | Marketing landing page |
| `/register/` | Signup |
| `/login/` | Login (+ 2FA step if enabled) |
| `/dashboard/` | Authenticated dashboard |
| `/settings/` | Profile, 2FA, danger zone |
| `/docs/` | Swagger UI |
| `/admin/` | Django admin |

---

## Testing

The project ships with a Django test suite of **45 tests** across three apps.

### What's covered

| File | Tests |
| ---- | ----- |
| `qr/tests.py` | QR service URL-scheme validation, CRUD ownership scoping, redirect + scan recording, image endpoint path-traversal protection |
| `users/tests.py` | Registration (happy path, password mismatch, short password), JWT login, profile GET/PUT/DELETE, `has_2fa` flag, full 2FA lifecycle (setup → confirm → verify → disable) with real TOTP codes |
| `analytics/tests.py` | Stats scoped to owner, 404 for other users' codes, aggregate counts |

### One-time setup

Django needs permission to create the test database. Grant it once:

```bash
sudo -u postgres psql -c "ALTER USER <your-db-user> CREATEDB;"
```

### Run the full suite

```bash
python manage.py test
```

First run takes ~75s (creating the DB + running every migration).

### Run fast (recommended for day-to-day)

```bash
python manage.py test --keepdb --parallel auto
```

- `--keepdb` reuses the test database between runs, skipping the slow DB creation + migrations step. Drops subsequent runs from ~75s to a few seconds.
- `--parallel auto` spreads tests across all CPU cores.

If you change a model, drop the cached test DB once so migrations re-apply:

```bash
dropdb test_qr_service && python manage.py test --keepdb
```

### Run a subset

```bash
python manage.py test qr                    # just the qr app
python manage.py test users.tests.TwoFactorConfirmTest    # one class
python manage.py test qr.tests.QRCodeServiceTest.test_accepts_http_and_https  # one test
```

---

## API Endpoints

All API endpoints return JSON and (except those noted) require a `Authorization: Bearer <access_token>` header.

### Auth (`/auth/`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register/` | public | Create account; triggers verification email |
| POST | `/auth/login/` | public | Returns `{access, refresh}` |
| POST | `/auth/refresh/` | public | Rotate refresh token |
| POST | `/auth/logout/` | user | Blacklists refresh token |
| GET | `/auth/me/` | user | Profile (includes `has_2fa`) |
| PUT | `/auth/me/` | user | Update profile |
| DELETE | `/auth/me/` | user | Delete account |
| POST | `/auth/2fa/setup/` | user | Returns QR code PNG + secret |
| POST | `/auth/2fa/confirm/` | user | Confirms TOTP code and activates 2FA |
| POST | `/auth/2fa/verify/` | user | Verifies code during login |
| POST | `/auth/2fa/disable/` | user | Disables 2FA (requires current code) |

### QR Codes (`/qr/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/qr/` | List the authenticated user's codes |
| POST | `/qr/` | Create a code from a URL |
| GET | `/qr/<id>/` | Retrieve a single code |
| PUT | `/qr/<id>/` | Update target URL |
| DELETE | `/qr/<id>/` | Delete code and its PNG |
| GET | `/qr/<id>/image/` | Serve the code's PNG (traversal-safe) |
| GET | `/qr/r/<slug>/` | **Public redirect** — records a scan, then 302s to the target URL |

### Analytics (`/analytics/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/` | Aggregate stats for the current user |
| GET | `/analytics/<qr_id>/` | Per-code scan history |

---

## Authentication Flow

### Signup
1. User submits email, username, password on `/register/`.
2. Frontend POSTs to `/auth/register/`.
3. Backend creates user (inactive-ish) and sends a verification email via allauth.
4. User clicks link in email → account is verified and can log in.

### Login (no 2FA)
1. User submits credentials on `/login/`.
2. Frontend POSTs to `/auth/login/` and receives `{access, refresh}`.
3. Tokens are stored in `localStorage`.
4. Redirect to `/dashboard/`.

### Login (with 2FA)
1. Same as above, but after receiving tokens the frontend calls `/auth/me/` and sees `has_2fa: true`.
2. The 2FA form is shown; the user enters the 6-digit TOTP code.
3. Frontend POSTs code to `/auth/2fa/verify/`.
4. On success, tokens are committed and user is redirected.

### Enabling 2FA
1. User clicks **Enable 2FA** on `/settings/`.
2. Backend creates an unconfirmed `TOTPDevice` and returns `{qr_code, secret}`.
3. User scans the QR with their authenticator app.
4. User enters the 6-digit code → `/auth/2fa/confirm/` marks the device confirmed.

---

## Security

The codebase has been through a full security audit. Implemented mitigations:

| Risk | Mitigation |
|------|------------|
| SSRF / malicious QR payloads | URL scheme allowlist (`http`, `https` only) enforced in `qr_service.py` and all `qr/views.py` entry points |
| Path traversal via media | `QRCodeImageView` resolves paths with `Path.resolve()` and verifies containment in `MEDIA_ROOT` |
| Orphaned files on delete | Delete handler removes the PNG after the DB row is deleted |
| XSS in templates | All user data rendered via `textContent` or `escapeHtml()`; `showAlert()` uses `textContent` |
| Missing CSRF / clickjacking | `XFrameOptionsMiddleware`, `CsrfViewMiddleware`, HSTS (prod), SSL redirect (prod) |
| Open redirect | Redirect view only sends users to URLs stored by authenticated code owners, and those URLs are scheme-validated |
| Token reuse after logout | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` |
| Brute force login / signup | DRF throttling + allauth `ACCOUNT_RATE_LIMITS` (`5/m/ip` for login & signup) |
| Weak passwords | Django's 4 built-in password validators |
| Secret leakage | `SECRET_KEY` is required from env, never hardcoded; `.env` blocked at the Claude Code level |

---

## Frontend Design System

The frontend takes visual cues from PiggyVest (Variant A palette):

| Token | Value |
|-------|-------|
| `--bg` | `#F7F7F3` (warm off-white) |
| `--bg-surface` | `#FFFFFF` |
| `--primary` | `#1A1D2E` (deep navy) |
| `--primary-hover` | `#0F1220` |
| `--accent` | `#E8526B` (coral) |
| `--text` | `#1A1D2E` |
| `--text-secondary` | `#5A5E6B` |
| `--border` | `#E7E5DF` |
| Font | DM Sans |

No gradients, no Tailwind, no React. Just hand-written CSS variables in `templates/base.html` and inline styles per page. All buttons, inputs, and cards use the same rounded-12–14px radius and a consistent 1.5px border.

---

## How the Frontend Talks to the Backend

1. Django serves an HTML template (e.g. `dashboard.html`).
2. The template's JavaScript calls the API via `fetch()`:
   ```js
   const resp = await fetch('/qr/', {
     headers: { Authorization: 'Bearer ' + getAccessToken() },
   });
   ```
3. Django REST Framework receives the request, validates the JWT (via `JWTAuthentication`), runs the view, and returns JSON.
4. The JavaScript renders the JSON into the DOM — always escaping user input via `textContent` or `escapeHtml()`.

Helpers in `base.html`:
- `apiCall(path, opts)` — `fetch` wrapper that auto-attaches the bearer token.
- `saveTokens() / clearTokens() / isLoggedIn()` — localStorage helpers.
- `showAlert(msg, type)` — XSS-safe toast.
- `escapeHtml(str)` — escape HTML entities for any place where `innerHTML` is unavoidable.

---

## Claude Code Integration

This project is set up to work safely with Claude Code.

- **`CLAUDE.md`** — project-level instructions Claude reads on every session. Includes rules like "NEVER read, access, display, or reference any `.env` files".
- **`.claude/settings.json`** — deny rules that block `.env` reads at the tool layer. Even if Claude ignored instructions, the tool call would be rejected.

Example deny block:

```json
{
  "permissions": {
    "deny": [
      "Read(.env*)",
      "Read(**/.env*)",
      "Bash(cat *.env*)",
      "Bash(printenv)"
    ]
  }
}
```

---

## Troubleshooting

**`DJANGO_SECRET_KEY environment variable is required`**
Your `.env` file is missing or not loaded. Make sure the file exists in the project root and contains `DJANGO_SECRET_KEY=...`. The check runs in `config/settings/development.py` after `.env` is loaded.

**`relation "auth_user" does not exist`**
Your database is either empty or shared with another project that never ran Django's auth migrations. Run `python manage.py migrate` against a fresh database.

**`SMTPSenderRefused` when signing up**
In dev, `EMAIL_BACKEND` is set to `console.EmailBackend`, so the verification link is printed to your `runserver` log — click it from there. For production, set SMTP env vars.

**2FA QR code won't scan**
Make sure you're using an authenticator app (Google Authenticator, Authy, 1Password), not a generic QR scanner. If the code doesn't match, verify your device clock is synced (TOTP is time-based).

**UI changes not showing**
Hard-refresh your browser (Ctrl+Shift+R / Cmd+Shift+R) to bypass the CSS cache.

---

## License

Private project. All rights reserved.
