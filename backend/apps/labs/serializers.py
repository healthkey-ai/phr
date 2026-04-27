"""
DRF serializers for the labs app — v2.

Endpoints:
  GET  /api/v1/labs/catalog/             → CatalogSerializer
  GET  /api/v1/labs/results/             → LabValueSerializer (list)
  POST /api/v1/labs/results/             → LabValueCreateSerializer
  GET  /api/v1/labs/results/{id}/        → LabValueSerializer
  DELETE /api/v1/labs/results/{id}/      → (no body)
"""
from rest_framework import serializers

from django.conf import settings

from .models import (
    LabTestEntry,
    LabValue,
    MatchMethod,
    ReferenceSource,
    UploadFile,
    UploadJob,
    UploadStatus,
    ValueType,
)
from .unit_converter import is_convertible, normalise  # noqa: F401


# ── Catalog ───────────────────────────────────────────────────────────────────


class LabTestEntrySerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = LabTestEntry
        fields = (
            "id",
            "abbreviation",
            "name",
            "default_unit",
            "alternative_units",
            "sample_values",
            "value_type",
            "molecular_weight",
            "category",
            "display_order",
        )

    def get_category(self, obj: LabTestEntry) -> str:
        return obj.category


class CatalogSerializer(serializers.Serializer):
    """Aggregated catalog payload for GET /catalog/."""
    tests = LabTestEntrySerializer(many=True)


# ── Lab values ───────────────────────────────────────────────────────────────


class LabValueSerializer(serializers.ModelSerializer):
    test = serializers.SerializerMethodField()
    upload = serializers.PrimaryKeyRelatedField(read_only=True)
    source_filename = serializers.SerializerMethodField()

    class Meta:
        model = LabValue
        fields = (
            "id",
            "test",
            "value",
            "value_qualitative",
            "unit",
            "source_text",
            "source_unit",
            "reference_min",
            "reference_max",
            "reference_source",
            "match_method",
            "source",
            "confidence",
            "status",
            "measured_at",
            "created_at",
            "upload",
            "source_filename",
        )
        read_only_fields = fields

    def get_source_filename(self, obj: LabValue) -> str:
        if obj.upload_id is None:
            return ""
        first = obj.upload.files.order_by("file_order", "id").first()
        return first.original_filename if first else ""

    def get_test(self, obj: LabValue) -> dict:
        t = obj.test_entry
        return {
            "id": t.id,
            "abbreviation": t.abbreviation,
            "name": t.name,
            "category": t.category,
            "default_unit": t.default_unit,
            "value_type": t.value_type,
        }


# ── Shared validation + normalisation helpers ─────────────────────────────

def _validate_value_fields(attrs: dict, test_entry: LabTestEntry) -> None:
    is_qualitative = test_entry.value_type == ValueType.QUALITATIVE
    has_value = attrs.get("value") is not None
    has_qualitative = bool(attrs.get("value_qualitative"))

    if is_qualitative and not has_qualitative:
        raise serializers.ValidationError(
            {"value_qualitative": "Qualitative tests require a value_qualitative."}
        )
    if not is_qualitative and not has_value:
        raise serializers.ValidationError({"value": "Numeric tests require a value."})

    if not is_qualitative:
        source_unit = (attrs.get("unit") or test_entry.default_unit or "").strip()
        target_unit = (test_entry.default_unit or "").strip()
        if source_unit == target_unit:
            return
        if not is_convertible(source_unit, target_unit, test_entry.molecular_weight):
            raise serializers.ValidationError(
                {
                    "unit": (
                        f"Cannot convert {source_unit!r} to {target_unit!r}. "
                        "Use the test's default unit or a compatible one."
                    )
                }
            )


def _apply_normalised_fields(
    validated_data: dict,
    test_entry: LabTestEntry,
    result: LabValue,
) -> None:
    is_qualitative = test_entry.value_type == ValueType.QUALITATIVE
    source_value = validated_data.get("value")
    source_unit = (validated_data.get("unit") or test_entry.default_unit or "").strip()
    target_unit = (test_entry.default_unit or "").strip()

    def _convert(n):
        if n is None:
            return None
        if source_unit == target_unit:
            return n
        return normalise(n, source_unit, target_unit, molecular_weight=test_entry.molecular_weight)

    if is_qualitative:
        result.value = None
        result.value_qualitative = validated_data.get("value_qualitative", "").strip()
        result.source_text = result.value_qualitative
    else:
        value = _convert(source_value)
        if value is None:
            raise serializers.ValidationError(
                {"value": "Unit conversion failed. Contact support if this persists."}
            )
        result.value = value
        result.value_qualitative = ""
        result.source_text = str(source_value)

    result.source_unit = source_unit
    result.unit = target_unit

    report_min = validated_data.get("reference_min")
    report_max = validated_data.get("reference_max")
    if report_min is not None and report_max is not None:
        result.reference_min = _convert(report_min)
        result.reference_max = _convert(report_max)
        result.reference_source = ReferenceSource.REPORT
    else:
        result.reference_min = None
        result.reference_max = None
        result.reference_source = ReferenceSource.NONE

    result.measured_at = validated_data.get("measured_at")


class LabValueCreateSerializer(serializers.Serializer):
    test_type_id = serializers.IntegerField()
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            test_entry = LabTestEntry.objects.get(pk=attrs["test_type_id"])
        except LabTestEntry.DoesNotExist:
            raise serializers.ValidationError({"test_type_id": "Unknown test type."})
        _validate_value_fields(attrs, test_entry)
        attrs["_test_entry"] = test_entry
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        test_entry: LabTestEntry = validated_data["_test_entry"]
        result = LabValue(
            user=request.user,
            test_entry=test_entry,
            loinc_entry=test_entry.loinc_entry,
            match_method=MatchMethod.MANUAL,
            source="manual",
            confidence=1.0,
        )
        _apply_normalised_fields(validated_data, test_entry, result)
        result.save()
        return result


class LabValueUpdateSerializer(serializers.Serializer):
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        if not self.instance:
            raise serializers.ValidationError("Update serializer requires an instance.")
        _validate_value_fields(attrs, self.instance.test_entry)
        return attrs

    def update(self, instance, validated_data):
        _apply_normalised_fields(validated_data, instance.test_entry, instance)
        instance.save()
        return instance


# ── Uploads ──────────────────────────────────────────────────────────────────


class UploadFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadFile
        fields = (
            "id",
            "original_filename",
            "mime_type",
            "size_bytes",
            "file_order",
            "sha256",
            "created_at",
        )
        read_only_fields = fields


class UploadJobSerializer(serializers.ModelSerializer):
    files = UploadFileSerializer(many=True, read_only=True)

    class Meta:
        model = UploadJob
        fields = (
            "id",
            "status",
            "provider",
            "lab_date",
            "notes",
            "parsed_results",
            "celery_task_id",
            "error_message",
            "files",
            "created_at",
            "completed_at",
        )
        read_only_fields = fields


# ── Upload create (multipart) ────────────────────────────────────────────────

_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
    ".heif": "image/heic",
}


def _sniff_mime(first_bytes: bytes) -> str | None:
    if first_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if first_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if first_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(first_bytes) >= 12:
        brand = first_bytes[4:12]
        if brand.startswith(b"ftyp") and brand[4:8] in (b"heic", b"heix", b"mif1", b"msf1"):
            return "image/heic"
    return None


class UploadJobCreateSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=settings.LAB_UPLOAD_MAX_FILES,
    )
    lab_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )

    def validate_files(self, files):
        max_file = settings.LAB_UPLOAD_MAX_FILE_BYTES
        max_total = settings.LAB_UPLOAD_MAX_TOTAL_BYTES
        accepted = settings.LAB_UPLOAD_ACCEPTED_MIME_TYPES

        total = 0
        seen_hashes: set[str] = set()
        annotated: list[dict] = []
        skipped_duplicate_names: list[str] = []

        for f in files:
            if f.size > max_file:
                raise serializers.ValidationError(
                    f"'{f.name}' is {_human_bytes(f.size)} (max {_human_bytes(max_file)} per file)."
                )
            total += f.size
            if total > max_total:
                raise serializers.ValidationError(
                    f"Total upload is {_human_bytes(total)} (max {_human_bytes(max_total)} per session)."
                )

            f.seek(0)
            head = f.read(12)
            f.seek(0)

            sniffed = _sniff_mime(head)
            ext_mime = _EXT_TO_MIME.get(_ext_of(f.name))
            detected = sniffed or ext_mime
            if detected not in accepted:
                raise serializers.ValidationError(
                    f"'{f.name}': unsupported file type. We accept PDF, JPEG, PNG, HEIC."
                )

            import hashlib
            h = hashlib.sha256()
            for chunk in f.chunks():
                h.update(chunk)
            sha256 = h.hexdigest()
            f.seek(0)

            if sha256 in seen_hashes:
                skipped_duplicate_names.append(f.name)
                continue
            seen_hashes.add(sha256)

            annotated.append({
                "file": f,
                "original_filename": f.name,
                "mime_type": detected,
                "file_order": len(annotated),
                "size_bytes": f.size,
                "sha256": sha256,
            })

        if not annotated:
            raise serializers.ValidationError("No valid files in request.")

        self.context["_skipped_duplicate_names"] = skipped_duplicate_names
        return annotated

    def create(self, validated_data):
        user = self.context["request"].user
        annotated = validated_data["files"]
        lab_date = validated_data.get("lab_date")
        notes = validated_data.get("notes", "")

        if len(annotated) == 1:
            hash_ = annotated[0]["sha256"]
            existing = (
                UploadJob.objects
                .filter(user=user, files__sha256=hash_)
                .exclude(status=UploadStatus.FAILED)
                .order_by("-created_at")
                .first()
            )
            if existing is not None:
                self.context["_dedup_hit"] = True
                return existing

        upload = UploadJob.objects.create(
            user=user,
            lab_date=lab_date,
            notes=notes,
        )
        for row in annotated:
            UploadFile.objects.create(
                upload=upload,
                file=row["file"],
                original_filename=row["original_filename"],
                mime_type=row["mime_type"],
                size_bytes=row["size_bytes"],
                file_order=row["file_order"],
                sha256=row["sha256"],
            )
        return upload


def _ext_of(filename: str) -> str:
    import os
    _, ext = os.path.splitext(filename or "")
    return ext.lower()


def _human_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


# ── Commit ──────────────────────────────────────────────────────────────────

_DUPLICATE_RELATIVE_TOLERANCE = 0.01


def _is_duplicate_value(user, result: LabValue) -> bool:
    if result.measured_at is None:
        return False

    qs = LabValue.objects.filter(
        user=user,
        test_entry=result.test_entry,
        measured_at=result.measured_at,
    )
    if result.test_entry.value_type == ValueType.QUALITATIVE:
        return qs.filter(value_qualitative=result.value_qualitative).exists()
    if result.value is None:
        return False
    for existing in qs.exclude(value__isnull=True).only("value"):
        denom = max(abs(existing.value), abs(result.value), 1e-9)
        if abs(existing.value - result.value) / denom <= _DUPLICATE_RELATIVE_TOLERANCE:
            return True
    return False


class _AcceptedRowSerializer(serializers.Serializer):
    source_index = serializers.IntegerField(min_value=0)
    test_type_id = serializers.IntegerField()
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            test_entry = LabTestEntry.objects.get(pk=attrs["test_type_id"])
        except LabTestEntry.DoesNotExist:
            raise serializers.ValidationError({"test_type_id": "Unknown test type."})
        _validate_value_fields(attrs, test_entry)
        attrs["_test_entry"] = test_entry
        return attrs


class UploadJobCommitSerializer(serializers.Serializer):
    accepted = serializers.ListField(
        child=_AcceptedRowSerializer(),
        allow_empty=True,
    )

    def validate(self, attrs):
        upload = self.context["upload"]
        parsed_count = len(upload.parsed_results or [])
        for row in attrs["accepted"]:
            if row["source_index"] >= parsed_count:
                raise serializers.ValidationError(
                    {"accepted": f"source_index {row['source_index']} is out of range "
                                 f"for this upload (parsed_results has {parsed_count})."}
                )
        return attrs

    def save(self, **kwargs):
        from django.db import transaction

        upload = self.context["upload"]
        user = self.context["request"].user
        parsed_results = upload.parsed_results or []

        saved: list[LabValue] = []
        skipped = 0

        with transaction.atomic():
            for row in self.validated_data["accepted"]:
                test_entry: LabTestEntry = row["_test_entry"]
                parsed = parsed_results[row["source_index"]]

                result = LabValue(
                    user=user,
                    test_entry=test_entry,
                    loinc_entry=test_entry.loinc_entry,
                    upload=upload,
                    source="document_extraction",
                    match_method=parsed.get("match_method") or MatchMethod.LOINC,
                    confidence=float(parsed.get("confidence", 0.0) or 0.0),
                )
                _apply_normalised_fields(row, test_entry, result)

                if _is_duplicate_value(user, result):
                    skipped += 1
                    continue

                result.save()
                saved.append(result)

        return {"saved": saved, "skipped": skipped}
