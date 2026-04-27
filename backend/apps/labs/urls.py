from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CatalogView, LabValueViewSet, UploadJobViewSet

router = DefaultRouter()
router.register(r"results", LabValueViewSet, basename="lab-result")
router.register(r"uploads", UploadJobViewSet, basename="lab-upload")

urlpatterns = [
    path("catalog/", CatalogView.as_view(), name="lab-catalog"),
    path("", include(router.urls)),
]
