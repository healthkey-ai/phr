"""
Labs views — Phase 2a + 2b.

GET    /api/v1/labs/catalog/                  → Catalog (categories + tests)
GET    /api/v1/labs/results/                  → Patient's lab history
POST   /api/v1/labs/results/                  → Manual entry
GET    /api/v1/labs/results/{id}/             → Single result
DELETE /api/v1/labs/results/{id}/             → Delete

POST   /api/v1/labs/uploads/                  → Create upload session (Phase 2b)
GET    /api/v1/labs/uploads/                  → List uploads (Records change log)
GET    /api/v1/labs/uploads/{id}/             → Poll upload status (Phase 2b)
"""
from django.conf import settings
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LabCategory, LabResult, LabTestType, LabUpload, LabUploadStatus
from .serializers import (
    CatalogSerializer,
    LabResultCreateSerializer,
    LabResultSerializer,
    LabResultUpdateSerializer,
    LabUploadCommitSerializer,
    LabUploadCreateSerializer,
    LabUploadSerializer,
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
            # prefetch upload.files for source_filename (§PF2 — N+1 guard)
            .prefetch_related("upload__files")
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


class LabUploadViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """/api/v1/labs/uploads/ — upload sessions (Phase 2b).

    POST creates a session with 1..10 files, enqueues the extraction task,
    and returns the LabUpload. The frontend polls GET /uploads/{id}/ until
    status is completed or failed.

    Scoped to request.user; other users' uploads 404.

    Dedup (per design §9.2): a single-file upload whose sha256 already lives
    on a non-failed LabUpload for this user returns the existing upload with
    HTTP 200 instead of creating a duplicate row.
    """

    # MultiPart for POST /uploads/ (file upload); JSON for POST /commit/ and
    # POST /extract/. DRF lets the content-type header pick the matching parser.
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)

    def get_queryset(self):
        return (
            LabUpload.objects
            .prefetch_related("files")
            .filter(user=self.request.user)
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return LabUploadCreateSerializer
        return LabUploadSerializer

    def create(self, request, *args, **kwargs):
        # Feature flag gate. Phase 2c ships disabled by default in prod; the
        # Render dashboard flip turns it on once Anthropic BAA is signed
        # (see design doc §9.4 + §15.1). Dev defaults to enabled.
        if not getattr(settings, "LAB_UPLOAD_ENABLED", False):
            raise PermissionDenied(
                "Lab report upload is not yet available. Enter values manually for now."
            )

        # DRF's ListField + FileField want the multipart key as `files`. DRF
        # normalises repeated form keys (`files=a&files=b`) into a list via
        # request.data.getlist(), but only if we pass the QueryDict through.
        # Extract explicitly so we handle both `files` (repeated) and
        # `files[]` (some clients) consistently.
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

        # Enqueue extraction only for freshly-created uploads. Dedup hits
        # already have (or had) a task in flight and we don't want to double-run.
        if not dedup_hit:
            from . import tasks  # local import avoids circular settings load
            task = tasks.process_lab_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save(update_fields=["celery_task_id"])
            # In eager mode (dev/tests without Redis), the task already ran
            # synchronously and mutated the row — pull the fresh state so the
            # response shows status=completed instead of pending.
            upload.refresh_from_db()

        return Response(
            LabUploadSerializer(upload).data,
            status=status.HTTP_200_OK if dedup_hit else status.HTTP_202_ACCEPTED,
        )

    # ── /uploads/{id}/commit/ ────────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        """Convert accepted parsed_results rows into LabResult records.

        Response payload mirrors LabResultSerializer for the newly-created
        rows, plus counts for UX feedback ('N saved, M skipped as duplicates').
        """
        upload = self.get_object()
        if upload.status != LabUploadStatus.COMPLETED:
            raise ValidationError(
                "This upload isn't ready to commit yet. Current status: "
                f"{upload.status}."
            )

        serializer = LabUploadCommitSerializer(
            data=request.data,
            context={"request": request, "upload": upload},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "saved_count": len(result["saved"]),
                "skipped_count": result["skipped"],
                "results": LabResultSerializer(result["saved"], many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    # ── /uploads/{id}/extract/ — retry a failed or stale extraction ──────
    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        """Re-enqueue the Celery extraction task for this upload.

        Used by the review UI's 'Try again' button after a failed extraction,
        and by Phase 2c's future prompt-tuning workflow to re-run extraction
        on an existing upload without re-uploading the files.
        """
        upload = self.get_object()
        # Reset transient fields so the next run starts clean
        upload.status = LabUploadStatus.PENDING
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
            LabUploadSerializer(upload).data,
            status=status.HTTP_202_ACCEPTED,
        )
