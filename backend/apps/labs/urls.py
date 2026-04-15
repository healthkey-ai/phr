from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CatalogView, LabResultViewSet

router = DefaultRouter()
router.register(r"results", LabResultViewSet, basename="lab-result")

urlpatterns = [
    path("catalog/", CatalogView.as_view(), name="lab-catalog"),
    path("", include(router.urls)),
]
