# QR Service

A Django REST API for generating QR codes, tracking scans, and viewing analytics.

## Project Structure

- `config/` - Django project settings (split into base/development/production)
- `qr/` - QR code generation and management (models, views, services)
- `analytics/` - Scan tracking and analytics
- `users/` - Authentication (JWT via SimpleJWT)
- `templates/` - Frontend HTML templates (landing, login, register, dashboard, settings)

## Tech Stack

- Python 3.12, Django 6.0, Django REST Framework
- PostgreSQL (via psycopg2-binary, dj-database-url)
- JWT authentication (djangorestframework-simplejwt)
- API docs via drf-spectacular (Swagger at `/docs/`)
- QR code generation via `qrcode` + `pillow`

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
