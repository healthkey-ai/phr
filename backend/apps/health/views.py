"""
Health check endpoints for deploy pipelines and uptime monitors.

Two tiers:
  - /health-check/       → liveness: process is running + can reach the DB
  - /health-check/ready/ → readiness: DB reachable and migrations applied

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

    Verifies the DB is reachable and migrations have been applied, so deploy
    gates can catch a release that booted against an unmigrated database.
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

        # Pending migrations — a booted-but-unmigrated instance must not
        # pass readiness.
        if ok:
            try:
                from django.db.migrations.executor import MigrationExecutor

                executor = MigrationExecutor(connections["default"])
                plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
                checks["migrations"] = "ok" if not plan else f"{len(plan)} pending"
                if plan:
                    ok = False
            except Exception as exc:  # noqa: BLE001
                checks["migrations"] = f"error: {exc}"
                ok = False

        payload = {
            "status": "ready" if ok else "not-ready",
            "service": "healthkey-backend",
            "checks": checks,
        }
        return Response(payload, status=200 if ok else 503)
