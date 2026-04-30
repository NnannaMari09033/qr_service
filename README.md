# QR Service

A full-stack Django application for generating QR codes, tracking scans, and viewing analytics. Built with Django REST Framework on the backend and vanilla HTML/CSS/JavaScript on the frontend.

Live at: https://qrservice-production-5d69.up.railway.app/

---

## Table of Contents

- [Overview](#overview)
- [Security Story](#security-story)
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
- [Frontend](#frontend)
- [How the Frontend Talks to the Backend](#how-the-frontend-talks-to-the-backend)
- [Deployment](#deployment)
- [Claude Code Integration](#claude-code-integration)
- [Troubleshooting](#troubleshooting)

---

## Overview

QR Service lets users:

1. Generate QR codes that redirect to any URL.
2. Track every scan (timestamp, IP, user agent).
3. View analytics and manage their codes from a dashboard.
4. Secure their account with TOTP-based 2FA.

The API is documented at `/docs/` (Swagger UI). The frontend is rendered directly by Django templates — no separate SPA build.

---

## Security Story

This project went through a deliberate security review. The findings below are the ones that materially shaped the codebase. The README leads with this section because the security model is the part of the project most worth understanding.

### 2FA bypass — caught and fixed

The first 2FA implementation issued a real JWT immediately after the password check, then asked the client to call `/auth/2fa/verify/` to "complete" login. That meant anyone with a valid password already held a working access token — the TOTP step was advisory, not enforced. Fixed by introducing a custom JWT type, [`Pre2FAToken`](users/tokens.py), with `token_type='pre_2fa'` and a 5-minute lifetime. The pre-token cannot authenticate any endpoint; the only place it is accepted is `/auth/2fa/verify/`, which exchanges it for real cookies after a TOTP code matches. Token-type binding is enforced by SimpleJWT, so even an attacker who somehow obtained a regular access token cannot present it at the verify endpoint. Tested at [`users/tests.py`](users/tests.py) (`TwoFactorLoginFlowTest`).

### Tokens out of localStorage, into HttpOnly cookies

Storing JWTs in `localStorage` means a single XSS = full account takeover. Migrated authentication to `HttpOnly` + `Secure` + `SameSite=Lax` cookies issued by the server. Cookies are inaccessible to JavaScript, the access cookie is scoped to `/`, the refresh cookie is scoped to `/auth/`, and a non-`HttpOnly` `is_authenticated` indicator cookie tells the frontend whether to render logged-in UI without ever exposing the token itself. Implemented in [`users/authentication.py`](users/authentication.py) and [`users/views.py`](users/views.py).

### Account deletion confirmation

Account deletion now requires the password (and a TOTP code if 2FA is enabled), validated server-side. A stolen access token cannot delete the account on its own. See [`ProfileView.delete`](users/views.py).

### Open-redirect mitigation

The redirect endpoint used to 302 to whatever URL the QR pointed at. That meant a phishing actor could host a QR that linked through `qrservice...up.railway.app/qr/redirect/<code>/` and inherit our domain's reputation. Now, anonymous and non-owner requests render a confirmation page that displays the destination URL; only `?go=1` follow-through (or an authenticated owner) triggers the actual redirect. Implemented in [`RedirectQRView`](qr/views.py) and [`templates/redirect_interstitial.html`](templates/redirect_interstitial.html).

### Brute-force surface

- `/auth/login/` and `/auth/2fa/verify/` are throttled at **10/minute per IP** ([`users/throttles.py`](users/throttles.py)).
- Anonymous `POST /qr/` is throttled at **5/hour** ([`qr/throttles.py`](qr/throttles.py)) so the public create endpoint cannot be used to flood the short-code namespace or fill disk.
- Authenticated traffic uses the default `100/minute` budget.

### Other hardening

- **URL scheme allowlist** on QR payloads (`http`/`https` only) — blocks `javascript:`, `data:`, `file:`, `ftp:`. Enforced in [`qr/services/qr_service.py`](qr/services/qr_service.py) and at every QR write entry point.
- **Path traversal protection** on `/qr/image/<code>.png` via `os.path.realpath` containment check ([`QRCodeImageView`](qr/views.py)).
- **Case-insensitive email + username uniqueness** ([`users/serializers.py`](users/serializers.py)) — Django's default `unique=True` is case-sensitive, which would let `Alice@x.com` and `alice@x.com` both register.
- **CSRF_TRUSTED_ORIGINS** correctly handles the `.up.railway.app` subdomain wildcard via `https://*.up.railway.app` ([`config/settings/production.py`](config/settings/production.py)).
- **Token rotation + blacklist** on every refresh.
- **HSTS, SSL redirect, secure cookies, content-type-nosniff** in production.

---

## Features

### Core
- QR code generation — any URL → scannable PNG (encodes the absolute redirect URL so phone scanners work without context).
- Scan tracking — every redirect records IP and user agent.
- Analytics dashboard — per-code totals and recent activity.
- Per-user ownership — users see and manage only their own codes.

### Authentication
- JWT in HttpOnly cookies (custom `CookieJWTAuthentication`).
- Optional TOTP 2FA via authenticator apps (Google Authenticator, Authy, 1Password).
- Pre2FA token type that gates real session cookies behind a verified TOTP code.
- Password + TOTP confirmation required for account deletion.

### Quality
- 64 automated tests covering QR CRUD, ownership scoping, scheme allowlist, path traversal, redirect interstitial, login flow, 2FA bypass attempts, cookie auth, throttling, account deletion, analytics scoping.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Web framework | Django 6.0 |
| API framework | Django REST Framework |
| Auth | djangorestframework-simplejwt + custom Pre2FAToken, django-otp |
| Database | PostgreSQL (via psycopg2-binary, dj-database-url) |
| QR generation | qrcode, pillow |
| API docs | drf-spectacular (Swagger UI) |
| Frontend | Django templates, vanilla JS, DM Sans font |
| Static files | whitenoise |
| Deployment | Railway (Nixpacks build, `railway.json` start command) |

---

## Project Structure

```
qr_service/
├── config/
│   ├── settings/
│   │   ├── base.py            Shared (apps, middleware, REST, JWT, throttle rates)
│   │   ├── development.py     Dev overrides (.env loading)
│   │   └── production.py      HSTS, SSL redirect, CSRF wildcard, whitenoise
│   ├── urls.py                Root URL router
│   ├── frontend_views.py      Renders the HTML templates
│   └── wsgi.py / asgi.py
├── qr/
│   ├── models.py              QRCode model
│   ├── views.py               CRUD + redirect (with interstitial) + image serving
│   ├── services/qr_service.py PNG generation, absolute-URL encoding, scheme allowlist
│   ├── throttles.py           AnonCreateQRThrottle (5/hour for anonymous POSTs)
│   └── urls.py
├── analytics/
│   ├── models.py              Scan model
│   ├── views.py               Per-user stats endpoints
│   └── urls.py
├── users/
│   ├── views.py               Register, login, logout, refresh, profile, 2FA, verify
│   ├── authentication.py      CookieJWTAuthentication (reads access cookie)
│   ├── tokens.py              Pre2FAToken (custom JWT type for 2FA gating)
│   ├── throttles.py           LoginRateThrottle (10/min for /auth/login/)
│   ├── serializers.py         RegisterSerializer with case-insensitive uniqueness
│   └── urls.py
├── templates/
│   ├── base.html              Layout, CSS variables, cookie-aware JS helpers
│   ├── landing.html
│   ├── login.html             Login + 2FA challenge (uses pre_auth_token in memory)
│   ├── register.html          Honest "account created — go log in" flow
│   ├── dashboard.html
│   ├── settings.html          Profile, 2FA, danger zone (password + TOTP delete)
│   └── redirect_interstitial.html  Open-redirect confirmation page
├── storage/                   Generated QR PNGs (MEDIA_ROOT)
├── manage.py
├── requirements.txt
├── railway.json               Railway build + startCommand (migrate then gunicorn)
├── Procfile                   Fallback deployment entrypoint
├── CLAUDE.md                  Instructions for Claude Code
└── .claude/settings.json      Tool-level deny rules for `.env`
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

Create a `.env` file in the project root (already gitignored and blocked from Claude Code):

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
| `DJANGO_SECRET_KEY` | yes | Django secret key. Validated on startup. |
| `DJANGO_DEBUG` | no | `True` in development, `False` (default) in production. |
| `DJANGO_ALLOWED_HOSTS` | prod | Comma-separated host list. |
| `DJANGO_SETTINGS_MODULE` | prod | `config.settings.production` |
| `DATABASE_URL` | alt | Full Postgres URL; takes precedence over `DB_*`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | alt | Discrete Postgres credentials. |

> **Note:** Email verification is currently disabled (`ACCOUNT_EMAIL_VERIFICATION = 'none'`). The dev email backend writes to the console. To enable real email, configure SMTP env vars and switch the backend in `base.py`.

---

## Running the App

```bash
# Development server (http://localhost:8000)
python manage.py runserver

# Tests
python manage.py test

# Create migrations after model changes
python manage.py makemigrations
python manage.py migrate

# Collect static files (prod)
python manage.py collectstatic --noinput
```

Routes once running:

| URL | Serves |
|-----|--------|
| `/` | Marketing landing page |
| `/register/` | Signup |
| `/login/` | Login (+ 2FA step if enabled) |
| `/dashboard/` | Authenticated dashboard |
| `/settings/` | Profile, 2FA, danger zone |
| `/docs/` | Swagger UI |
| `/admin/` | Django admin |
| `/qr/redirect/<code>/` | Public redirect (interstitial for non-owners) |

---

## Testing

64 tests across `qr/`, `users/`, `analytics/`.

| File | Coverage |
|------|----------|
| [`qr/tests.py`](qr/tests.py) | URL-scheme validation, CRUD ownership scoping, redirect interstitial (anonymous, owner, non-owner, `?go=1`), image path-traversal protection, anonymous QR throttle |
| [`users/tests.py`](users/tests.py) | Registration (happy path, duplicate email/username case-insensitive, mismatched/short password), cookie login (no-2FA path), 2FA login flow (pre-token cannot authenticate, regular access token rejected at verify endpoint, valid TOTP issues full cookies), cookie refresh, logout, profile GET/PUT, account deletion (password required, TOTP required when 2FA enabled), full 2FA setup/confirm/disable lifecycle, login throttle |
| [`analytics/tests.py`](analytics/tests.py) | Stats scoped to owner, 404 for other users' codes |

### One-time setup

Django needs CREATEDB on its database role:

```bash
sudo -u postgres psql -c "ALTER USER <your-db-user> CREATEDB;"
```

### Run

```bash
python manage.py test                            # full suite, ~3 minutes first run
python manage.py test --keepdb --parallel auto   # day-to-day, much faster
python manage.py test users.tests.TwoFactorLoginFlowTest
```

If you change a model, drop the cached test DB once:

```bash
dropdb test_qr_service && python manage.py test --keepdb
```

---

## API Endpoints

All API endpoints return JSON. Authenticated endpoints accept either an auth cookie (set by the login flow) **or** an `Authorization: Bearer <access_token>` header (used by tests / curl).

### Auth (`/auth/`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register/` | public | Create account |
| POST | `/auth/login/` | public | Set HttpOnly cookies, or return `pre_auth_token` if 2FA |
| POST | `/auth/2fa/verify/` | public | Exchange `pre_auth_token` + TOTP code for real cookies |
| POST | `/auth/refresh/` | public | Rotate refresh cookie, set new access cookie |
| POST | `/auth/logout/` | public | Blacklist refresh, clear all auth cookies |
| GET | `/auth/me/` | user | Profile (includes `has_2fa`) |
| PUT | `/auth/me/` | user | Update profile |
| DELETE | `/auth/me/` | user | Delete account (requires password + TOTP if 2FA on) |
| POST | `/auth/2fa/setup/` | user | Returns enrolment QR code + secret |
| POST | `/auth/2fa/confirm/` | user | Confirm enrolment with first TOTP code |
| POST | `/auth/2fa/disable/` | user | Disable 2FA (requires current TOTP code) |

### QR Codes (`/qr/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/qr/` | List the authenticated user's codes |
| POST | `/qr/` | Create a code from a URL |
| GET | `/qr/<short_code>/` | Retrieve a single code |
| PUT | `/qr/<short_code>/` | Update target URL |
| DELETE | `/qr/<short_code>/` | Delete code |
| GET | `/qr/image/<short_code>.png` | Serve the PNG (path-traversal-safe) |
| GET | `/qr/redirect/<short_code>/` | **Public redirect** — interstitial for non-owners; `?go=1` to follow through |

### Analytics (`/analytics/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/` | Aggregate stats for the current user |
| GET | `/analytics/<short_code>/` | Per-code scan history |

---

## Authentication Flow

### Signup
1. User submits username + email + password on `/register/`.
2. Frontend POSTs to `/auth/register/`.
3. Backend creates the account.
4. UI shows "Account created — go log in".

### Login (no 2FA)
1. POST to `/auth/login/`.
2. Backend verifies credentials, sets three cookies on the response: `access_token` (HttpOnly), `refresh_token` (HttpOnly, scoped to `/auth/`), `is_authenticated` (readable, used only to render logged-in UI).
3. Frontend redirects to `/dashboard/`.

### Login (with 2FA)
1. POST to `/auth/login/` — backend sees a confirmed TOTPDevice and returns `{ requires_2fa: true, pre_auth_token: "..." }`. **No auth cookies are set.**
2. Frontend keeps `pre_auth_token` in a JS variable in memory only and prompts for the 6-digit code.
3. POST to `/auth/2fa/verify/` with `{ pre_auth_token, code }`.
4. Backend validates the token type is `pre_2fa`, looks up the user, checks the TOTP code against the device, and only then sets the real auth cookies.

### Subsequent requests
- Browser sends cookies automatically via `credentials: 'include'`.
- `CookieJWTAuthentication` reads the access cookie (or falls back to a Bearer header for tests/curl) and resolves the user.
- On 401, the frontend tries `/auth/refresh/` once; if that fails, it clears the indicator cookie and redirects to `/login/`.

---

## Security

| Risk | Mitigation |
|------|------------|
| 2FA bypass | `Pre2FAToken` with token-type binding — pre-token cannot authenticate any endpoint, only `/auth/2fa/verify/` accepts it |
| XSS → token theft | Tokens in `HttpOnly` + `Secure` + `SameSite=Lax` cookies; `localStorage` no longer used |
| CSRF | `SameSite=Lax` cookies, Django CSRF middleware, `CSRF_TRUSTED_ORIGINS` configured for the deployed origin |
| Open redirect | Confirmation interstitial shown to non-owners on `/qr/redirect/<code>/` |
| SSRF / malicious QR payloads | Scheme allowlist (`http`, `https`) at every write path |
| Path traversal via media | `os.path.realpath` containment check inside `MEDIA_ROOT/qr_codes` |
| Brute-force login | `LoginRateThrottle` 10/min per IP on `/auth/login/` and `/auth/2fa/verify/` |
| Anonymous QR flooding | `AnonCreateQRThrottle` 5/hour per IP on `POST /qr/` |
| Account takeover via stolen access token | Account deletion requires password (and TOTP if 2FA on) |
| Duplicate-account spoofing | Case-insensitive uniqueness on username and email |
| Token reuse after logout | `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` |
| Weak passwords | Django's 4 built-in password validators |
| Secret leakage | `SECRET_KEY` required from env; `.env` blocked at the Claude Code tool layer |
| HTTPS downgrade (prod) | `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*` |

---

## Frontend

Hand-written CSS variables in [`templates/base.html`](templates/base.html) — no Tailwind, no React, no build step. Each page extends `base.html` and adds inline styles or a `<style>` block.

Cookie-aware JS helpers (in `base.html`):
- `isLoggedIn()` — reads the readable `is_authenticated` cookie.
- `clearAuthIndicator()` — clears that indicator on logout.
- `apiCall(path, opts)` — `fetch` wrapper that uses `credentials: 'include'` and auto-refreshes on 401.
- `logout()` — POSTs to `/auth/logout/`, clears the indicator, redirects home.
- `escapeHtml(str)` — escape for the rare cases `innerHTML` is unavoidable.
- `showAlert(msg, type)` — `textContent`-based toast (XSS-safe).

---

## How the Frontend Talks to the Backend

1. Django serves a template (e.g. `dashboard.html`).
2. The template's JS calls `apiCall('/qr/', {...})`.
3. The browser attaches the `access_token` cookie automatically because `credentials: 'include'` is set.
4. `CookieJWTAuthentication` reads it server-side and resolves the user.
5. DRF validates, runs the view, returns JSON.
6. JS renders the JSON via `textContent` or `escapeHtml()` — no `innerHTML` of unescaped user data.

---

## Deployment

Deployed to Railway. Two deployment files live in the repo:

- [`railway.json`](railway.json) — Nixpacks build + start command. The start command runs migrations on every deploy *before* gunicorn starts: `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`. Without the inline migrate, fresh databases hit `relation "..." does not exist` on first request.
- [`Procfile`](Procfile) — fallback deployment entrypoint.

Production-only settings live in [`config/settings/production.py`](config/settings/production.py):
- HSTS (1 year, includeSubDomains, preload).
- `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` for the Railway HTTPS terminator.
- `whitenoise` middleware for static files.
- `CSRF_TRUSTED_ORIGINS` derived from `ALLOWED_HOSTS`, with `https://*.up.railway.app` subdomain wildcard handling.

---

## Claude Code Integration

This project is set up to work safely with Claude Code.

- **`CLAUDE.md`** — project-level instructions Claude reads on every session. Includes the rule "NEVER read, access, display, or reference any `.env` files".
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
Your `.env` is missing or not loaded. Make sure it's in the project root and contains `DJANGO_SECRET_KEY=...`.

**`relation "..." does not exist` on Railway**
Migrations haven't run. Confirm `railway.json` `startCommand` runs `migrate --noinput` before `gunicorn`. The fix is in this repo, but if you forked an older version, that's the cause.

**Phone scanner "doesn't open the QR"**
The QR encodes the absolute redirect URL using `request.build_absolute_uri()`, so it should always open. If it doesn't, check that the QR was generated *after* commit `8c53232` — older QRs encode a relative path and won't resolve outside the browser tab they were created in.

**Login returns `requires_2fa: true` but no cookies**
That's intentional. The frontend must call `/auth/2fa/verify/` with the `pre_auth_token` and a TOTP code to complete login.

**`429 Too Many Requests` on `/auth/login/`**
Throttle is 10/minute per IP. Wait a minute or test from a different network.

**2FA QR code won't scan**
Use an authenticator app (Google Authenticator, Authy, 1Password), not a generic QR scanner. If codes don't match, check device clock sync — TOTP is time-based.

**UI changes not showing**
Hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) to bypass the CSS cache.

---

## License

Private project. All rights reserved.
