# HealthKey Backend

Django 5 + DRF backend for the HealthKey patient app.

## Quick start (local SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API will be live at http://localhost:8000/api/v1/

## Quick start (Docker + Postgres)

```bash
docker compose up --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
```

## Endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/auth/register/` | none |
| POST | `/api/v1/auth/login/` | none |
| POST | `/api/v1/auth/token/refresh/` | none |
| GET | `/api/v1/auth/me/` | JWT |
| GET | `/api/v1/patient-info/user/` | JWT |
| PATCH | `/api/v1/patient-info/user/` | JWT |
| GET | `/api/v1/patient-info/profile-completeness/` | JWT |
| GET | `/api/v1/form-settings/` | JWT |

## Tests

```bash
pytest
```
