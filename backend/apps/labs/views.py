"""
Labs views — v2.

GET    /api/v1/labs/catalog/                  → Catalog (tests)
GET    /api/v1/labs/results/                  → Patient's lab history
POST   /api/v1/labs/results/                  → Manual entry
GET    /api/v1/labs/results/{id}/             → Single result
DELETE /api/v1/labs/results/{id}/             → Delete

POST   /api/v1/labs/uploads/                  → Create upload session
GET    /api/v1/labs/uploads/                  → List uploads
GET    /api/v1/labs/uploads/{id}/             → Poll upload status
DELETE /api/v1/labs/uploads/{id}/             → Delete upload + associated values
"""
from django.conf import settings
import logging

from rest_framework import mixins, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LabTestEntry, LabValue, UploadJob, UploadStatus

logger = logging.getLogger(__name__)
from .serializers import (
    CatalogSerializer,
    LabValueCreateSerializer,
    LabValueSerializer,
    LabValueUpdateSerializer,
    UploadJobCommitSerializer,
    UploadJobCreateSerializer,
    UploadJobSerializer,
)


class CatalogView(APIView):
    """GET /api/v1/labs/catalog/ — all test entries."""

    def get(self, request, *args, **kwargs):
        tests = LabTestEntry.objects.all()
        serializer = CatalogSerializer({"tests": tests})
        return Response(serializer.data)


class LabValueViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """/api/v1/labs/results/ — patient's lab values."""

    def get_queryset(self):
        qs = (
            LabValue.objects.select_related("test_entry")
            .prefetch_related("upload__files")
            .filter(user=self.request.user)
            .order_by("-measured_at", "-created_at")
        )
        test_abbrev = self.request.query_params.get("test")
        if test_abbrev:
            qs = qs.filter(test_entry__abbreviation=test_abbrev)
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(measured_at__gte=date_from)
        if date_to:
            qs = qs.filter(measured_at__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return LabValueCreateSerializer
        if self.action in ("update", "partial_update"):
            return LabValueUpdateSerializer
        return LabValueSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            LabValueSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(LabValueSerializer(result).data)


class UploadJobViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """/api/v1/labs/uploads/ — upload sessions."""

    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    def get_queryset(self):
        return (
            UploadJob.objects
            .prefetch_related("files")
            .filter(user=self.request.user)
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return UploadJobCreateSerializer
        return UploadJobSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.check_stale_processing()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if not getattr(settings, "LAB_UPLOAD_ENABLED", False):
            raise PermissionDenied(
                "Lab report upload is not yet available. Enter values manually for now."
            )

        raw = request.data
        files = raw.getlist("files") if hasattr(raw, "getlist") else raw.get("files", [])
        if not files and hasattr(raw, "getlist"):
            files = raw.getlist("files[]")
        payload = {
            "files": files,
            "lab_date": raw.get("lab_date"),
            "notes": raw.get("notes", ""),
        }
        serializer = self.get_serializer(
            data=payload,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        upload = serializer.save()
        dedup_hit = bool(serializer.context.get("_dedup_hit"))

        if not dedup_hit:
            from . import tasks
            task = tasks.process_lab_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save(update_fields=["celery_task_id"])
            upload.refresh_from_db()

        return Response(
            UploadJobSerializer(upload).data,
            status=status.HTTP_200_OK if dedup_hit else status.HTTP_202_ACCEPTED,
        )

    def perform_destroy(self, instance):
        values_deleted, _ = LabValue.objects.filter(upload=instance).delete()
        for uf in instance.files.all():
            if uf.file:
                uf.file.delete(save=False)
        logger.info(
            "upload_delete: job=%d user=%d — deleted %d lab values, %d files",
            instance.pk, instance.user_id, values_deleted, instance.files.count(),
        )
        instance.delete()

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        upload = self.get_object()
        if upload.status != UploadStatus.COMPLETED:
            raise ValidationError(
                "This upload isn't ready to commit yet. Current status: "
                f"{upload.status}."
            )

        serializer = UploadJobCommitSerializer(
            data=request.data,
            context={"request": request, "upload": upload},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "saved_count": len(result["saved"]),
                "skipped_count": result["skipped"],
                "results": LabValueSerializer(result["saved"], many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        upload = self.get_object()
        upload.status = UploadStatus.PENDING
        upload.error_message = ""
        upload.parsed_results = []
        upload.completed_at = None
        upload.save(update_fields=["status", "error_message", "parsed_results", "completed_at"])

        from . import tasks
        task = tasks.process_lab_upload.delay(upload.id)
        upload.celery_task_id = task.id
        upload.save(update_fields=["celery_task_id"])
        upload.refresh_from_db()

        return Response(
            UploadJobSerializer(upload).data,
            status=status.HTTP_202_ACCEPTED,
        )
