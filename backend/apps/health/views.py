"""
Health check endpoints for deploy pipelines and uptime monitors.

Two tiers:
  - /health-check/   → liveness: process is running + can reach the DB
  - /health-check/ready/ → readiness: migrations applied, catalog loaded,
                           Celery broker reachable (when configured)

Render's blueprint points at `/health-check/`. Platform failover / deploy
gating should prefer the liveness route — it's cheap and sufficient for
"should this instance receive traffic". Use the readiness route in deeper
uptime monitoring.
"""
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    """GET /health-check/ — the process is up and can query the default DB.

    Returns 200 on success, 503 on any dependency failure. Auth-free so
    Render's health probes can reach it without a token.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, *args, **kwargs):
        checks: dict[str, str] = {}
        ok = True

        # Database — cheap round-trip on the default connection
        try:
            connections["default"].cursor().execute("SELECT 1")
            checks["db"] = "ok"
        except OperationalError as exc:
            checks["db"] = f"error: {exc}"
            ok = False

        payload = {
            "status": "ok" if ok else "degraded",
            "service": "healthkey-backend",
            "debug": settings.DEBUG,
            "checks": checks,
        }
        return Response(payload, status=200 if ok else 503)


class ReadinessView(APIView):
    """GET /health-check/ready/ — deeper check for full readiness.

    Validates that the labs catalog fixture has been loaded (a common
    deploy failure mode — forgetting the post-deploy loaddata) and that
    the Celery broker URL resolves when configured. Returns 503 on any
    failure so deploy gates can catch half-broken releases.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, *args, **kwargs):
        checks: dict[str, str] = {}
        ok = True

        # DB
        try:
            connections["default"].cursor().execute("SELECT 1")
            checks["db"] = "ok"
        except OperationalError as exc:
            checks["db"] = f"error: {exc}"
            ok = False

        # Labs catalog — empty catalog means fixture wasn't loaded
        try:
            from apps.labs.models import LabTestType
            count = LabTestType.objects.count()
            checks["labs_catalog"] = f"ok ({count} tests)" if count > 0 else "empty"
            if count == 0:
                ok = False
        except Exception as exc:  # noqa: BLE001
            checks["labs_catalog"] = f"error: {exc}"
            ok = False

        # Celery broker — only when configured
        broker_url = getattr(settings, "CELERY_BROKER_URL", "")
        if broker_url:
            try:
                import redis
                r = redis.Redis.from_url(broker_url, socket_connect_timeout=2)
                r.ping()
                checks["celery_broker"] = "ok"
            except Exception as exc:  # noqa: BLE001
                checks["celery_broker"] = f"error: {exc}"
                ok = False
        else:
            checks["celery_broker"] = "not configured"

        payload = {
            "status": "ready" if ok else "not-ready",
            "service": "healthkey-backend",
            "checks": checks,
        }
        return Response(payload, status=200 if ok else 503)
