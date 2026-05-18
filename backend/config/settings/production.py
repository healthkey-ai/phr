"""
Production settings. Loaded when DJANGO_SETTINGS_MODULE=config.settings.production.
"""
from .base import *  # noqa: F401, F403
from .base import env

DEBUG = False

# Render runs the service behind its own proxy that terminates TLS. We trust
# the X-Forwarded-Proto header so Django knows the request came in over HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Render sets RENDER_EXTERNAL_HOSTNAME to the service's public domain; add it
# to ALLOWED_HOSTS automatically so the env var list stays minimal in the
# blueprint.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, RENDER_EXTERNAL_HOSTNAME]  # noqa: F405
