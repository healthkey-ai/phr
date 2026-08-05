"""
Production settings — PostgreSQL, DEBUG=False, restricted CORS.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Cloud Run terminates SSL and forwards HTTP internally.
# Trust the X-Forwarded-Proto header so Django knows the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
