"""
Base Django settings for HealthKey patient app.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    JWT_ACCESS_LIFETIME_MINUTES=(int, 15),
    JWT_REFRESH_LIFETIME_DAYS=(int, 7),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Local apps
    "apps.accounts",
    "apps.patient_profile",
    "apps.labs",
    "apps.health",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR}/db.sqlite3"),
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Logging ─────────────────────────────────────────────────────────────────
# Without an explicit config, Django's default root-logger threshold is
# WARNING for non-Django loggers — which means our app-level
# `logger.info(...)` lines (e.g. `process_lab_upload starting`) vanish in
# dev. Route `apps.*` at INFO to the console so Celery-eager tasks produce
# visible output. Override LOG_LEVEL in env for deeper debugging.
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "app": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "app",
        },
    },
    "loggers": {
        # Our app modules. Captures apps.labs.tasks, apps.labs.parsers.*, etc.
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        # Celery's own internal logging (task dispatch, eager-mode traces).
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# User-uploaded files (Phase 2b: lab reports). Production swaps this out for
# S3 via django-storages (§9.1 of the lab upload design doc) — deferred to a
# later landing. Local dev writes under MEDIA_ROOT/lab-uploads/YYYY/MM/.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Hard caps enforced at the view layer. Keep them here as the source of truth
# so serializers, tests, and the frontend all read the same numbers.
LAB_UPLOAD_MAX_FILE_BYTES = 10 * 1024 * 1024       # 10 MB per file
LAB_UPLOAD_MAX_TOTAL_BYTES = 20 * 1024 * 1024      # 20 MB per upload session
LAB_UPLOAD_MAX_FILES = 10                          # per upload session
LAB_UPLOAD_ACCEPTED_MIME_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_LIFETIME_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_LIFETIME_DAYS")),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ── Celery / Redis ────────────────────────────────────────────────────────────
# Phase 2b ships the first real task (apps.labs.process_lab_upload, currently
# a stub). Production services set CELERY_BROKER_URL + CELERY_RESULT_BACKEND
# to the Render Redis service. Local dev and tests run without Redis by
# falling back to always-eager mode: .delay() executes inline, which is
# exactly what we want for a stub that returns in <1ms.
# ── Lab upload feature flag + LLM config (Phase 2c) ─────────────────────────
# LAB_UPLOAD_ENABLED gates the POST /api/v1/labs/uploads/ endpoint. Disabled
# by default in production until the relevant BAA is on file; dashboard flip
# turns it on when ready. Local dev defaults to enabled so you can exercise
# the flow without env vars.
LAB_UPLOAD_ENABLED = env.bool("LAB_UPLOAD_ENABLED", default=True)

# Which LLM to use for extraction. "claude" (default) or "openai". Picked at
# task-dispatch time by apps.labs.parsers.llm_parser. Swapping requires only
# setting the env var — task + matcher + pipeline are provider-agnostic.
LAB_LLM_PROVIDER = env("LAB_LLM_PROVIDER", default="claude")

# Claude API key — injected via env, never committed. Empty string means the
# LLM parser raises ExtractionError on first call when LAB_LLM_PROVIDER="claude";
# the task catches this and marks the upload failed with a configuration-
# specific message.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# OpenAI API key + model. Same semantics as ANTHROPIC_API_KEY. gpt-4o gets
# us the best accuracy on lab-report extraction; gpt-4o-mini is a cheaper
# fallback that's still usable on clean typeset PDFs. Override via env.
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
LAB_OPENAI_MODEL = env("LAB_OPENAI_MODEL", default="gpt-4o")

_BROKER_URL = env("CELERY_BROKER_URL", default="")
# Eager mode needs *some* transport configured even though it never connects.
# "memory://" keeps kombu quiet and works with always-eager in tests / dev.
CELERY_BROKER_URL = _BROKER_URL or "memory://"
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="cache+memory://")
CELERY_TASK_ALWAYS_EAGER = not bool(_BROKER_URL)
CELERY_TASK_EAGER_PROPAGATES = True  # surface task exceptions in tests
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SOFT_TIME_LIMIT = 270  # 4.5 min — matches design doc §6 for LLM jobs
CELERY_TASK_TIME_LIMIT = 300        # 5 min hard limit
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
