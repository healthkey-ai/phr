"""
Labs views — Phase 2a.

GET  /api/v1/labs/catalog/                  → Catalog (categories + tests)
GET  /api/v1/labs/results/                  → Patient's lab history
POST /api/v1/labs/results/                  → Manual entry
GET  /api/v1/labs/results/{id}/             → Single result
DELETE /api/v1/labs/results/{id}/           → Delete
"""
from rest_framework import generics, mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LabCategory, LabResult, LabTestType
from .serializers import (
    CatalogSerializer,
    LabResultCreateSerializer,
    LabResultSerializer,
    LabResultUpdateSerializer,
)


class CatalogView(APIView):
    """GET /api/v1/labs/catalog/ — single payload with all categories + tests.

    Heavily cached on the frontend (24h staleTime). Backend query is cheap
    (~35 tests + 7 categories) but still uses select_related for hygiene (§PF4).
    """

    def get(self, request, *args, **kwargs):
        categories = LabCategory.objects.all()
        tests = LabTestType.objects.select_related("category").all()
        serializer = CatalogSerializer({"categories": categories, "tests": tests})
        return Response(serializer.data)


class LabResultViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """/api/v1/labs/results/ — patient's lab results.

    - GET (list) supports ?test=<abbreviation>, ?from=YYYY-MM-DD, ?to=YYYY-MM-DD
    - POST creates a manual entry (unit-normalised server-side)
    - PATCH updates value/unit/date/range on an existing row; test_type is
      immutable (CreateModelMixin-only-for-test-identity). Unit conversion
      re-runs so you can edit hgb from g/dL to g/L without creating a new row.
    - DELETE removes the row (cascade pseudonymises audit refs — §9.5)

    Scoped to request.user; other users' results 404.
    """

    def get_queryset(self):
        # select_related prevents N+1 on list views (§PF2)
        qs = (
            LabResult.objects.select_related("test_type", "test_type__category")
            .filter(user=self.request.user)
            .order_by("-measured_at", "-created_at")
        )
        test_abbrev = self.request.query_params.get("test")
        if test_abbrev:
            qs = qs.filter(test_type__abbreviation=test_abbrev)
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(measured_at__gte=date_from)
        if date_to:
            qs = qs.filter(measured_at__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return LabResultCreateSerializer
        if self.action in ("update", "partial_update"):
            return LabResultUpdateSerializer
        return LabResultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            LabResultSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        # Return the read serializer shape so the frontend sees a consistent
        # response format across create/read/update.
        return Response(LabResultSerializer(result).data)
