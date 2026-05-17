"""
Celery application bootstrap.

Phase 2a: no tasks defined yet — this file exists so the worker service
can boot and register itself with the broker, so the deploy pipeline and
Render blueprint infrastructure are in place before Phase 2b starts
wiring up the extraction pipeline.

Celery auto-discovers tasks from any installed app's `tasks.py` module.
When `apps/labs/tasks.py` lands in Phase 2b, it'll be picked up automatically.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("healthkey")

# Pulls all settings starting with CELERY_ from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Find tasks.py in any INSTALLED_APPS module
app.autodiscover_tasks()


@app.on_after_finalize.connect
def _verify_native_deps(sender, **kwargs):
    """Fail fast at worker boot if critical native libraries are broken."""
    import importlib
    for mod in ("fitz", "anthropic"):
        try:
            importlib.import_module(mod)
        except Exception as e:
            raise SystemExit(
                f"[FATAL] Cannot import '{mod}': {e}\n"
                f"The Celery worker cannot process lab uploads without it. "
                f"Run: pip install -r requirements.txt"
            )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Smoke test task. Invoke with `celery -A config call config.celery.debug_task`."""
    print(f"Celery debug task fired — request: {self.request!r}")
