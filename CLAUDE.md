# QR Service

A Django REST API for generating QR codes, tracking scans, and viewing analytics. Open source under MIT license.

## Project Structure

- `config/` - Django project settings (split into base/development/production)
- `qr/` - QR code generation and management. PNGs are rendered on demand from DB rows; no filesystem state.
- `analytics/` - Scan tracking and per-code stats
- `users/` - Cookie-based JWT auth, custom Pre2FAToken type for 2FA gating, TOTP via django-otp
- `templates/` - Server-rendered HTML (landing, login, register, dashboard, settings, redirect interstitial)

## Tech Stack

- Python 3.12, Django 6.0, Django REST Framework
- PostgreSQL (via psycopg2-binary, dj-database-url)
- Authentication: SimpleJWT tokens delivered in HttpOnly cookies via `users/authentication.py:CookieJWTAuthentication`
- 2FA: django-otp TOTPDevice; login flow uses a custom `Pre2FAToken` JWT type that only `/auth/2fa/verify/` accepts
- API docs via drf-spectacular (Swagger at `/docs/`)
- QR code generation via `qrcode` + `pillow`, rendered in memory (`qr/services/qr_service.py:render_qr_png`)

## Commands

- `python manage.py runserver` - Start dev server (uses `config.settings.development`)
- `python manage.py makemigrations` - Create migrations
- `python manage.py migrate` - Apply migrations
- `python manage.py test` - Run tests

## Environment

- All secrets and config are loaded from environment variables (see `config/settings/base.py`)
- Virtual environment: `venv/`

## Rules

- NEVER read, access, display, or reference any `.env` files or their contents
- NEVER commit `.env` files or any file containing secrets
- Do not modify files in `venv/`
