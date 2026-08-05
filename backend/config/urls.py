import re
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path

urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/profile/", include("apps.patient_profile.urls")),
    path("api/v1/health/", include("apps.health.urls")),
]


# SPA catch-all: serve index.html for any non-API/non-static route
_index_html = Path(settings.WHITENOISE_ROOT or "") / "index.html"
if _index_html.exists():
    _index_content = _index_html.read_text()

    def _spa_index(request):
        response = HttpResponse(_index_content, content_type="text/html")
        response["Cache-Control"] = "no-store, must-revalidate"
        return response

    _admin_prefix = re.escape(settings.ADMIN_URL_PATH)
    urlpatterns += [re_path(rf"^(?!api/|{_admin_prefix}|static/).*$", _spa_index)]
