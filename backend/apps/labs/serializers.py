"""
DRF serializers for the labs app.

Phase 2a endpoints:
  GET  /api/v1/labs/catalog/             → CatalogSerializer
  GET  /api/v1/labs/results/             → LabResultSerializer (list)
  POST /api/v1/labs/results/             → LabResultCreateSerializer
  GET  /api/v1/labs/results/{id}/        → LabResultSerializer
  DELETE /api/v1/labs/results/{id}/      → (no body)
"""
from rest_framework import serializers

from django.conf import settings

from .models import (
    LabCategory,
    LabResult,
    LabTestType,
    LabUpload,
    LabUploadFile,
    LabUploadStatus,
    MatchMethod,
    ReferenceSource,
    ValueType,
)
from .unit_converter import is_convertible, normalise  # noqa: F401


# ── Catalog ───────────────────────────────────────────────────────────────────

class LabCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabCategory
        fields = ("key", "name", "display_order")


class LabTestTypeSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="key", read_only=True)
    reference_ranges_by_unit = serializers.SerializerMethodField()

    class Meta:
        model = LabTestType
        fields = (
            "id",
            "abbreviation",
            "name",
            "loinc_code",
            "default_unit",
            "alternative_units",
            "sample_values",
            "reference_ranges",
            "reference_ranges_by_unit",
            "value_type",
            "molecular_weight",
            "category",
            "display_order",
        )

    def get_reference_ranges_by_unit(self, obj: LabTestType) -> dict[str, list[float]]:
        """Pre-compute the reference range in every unit the UI may render.

        Keys: default_unit + each alternative_unit.
        Values: [min, max] as floats, converted via unit_converter (same code
        path used on LabResult save, so the numbers match).

        Returns {} when the test has no default range (e.g. qualitative
        infection screens, or M-spike where "default": [0, 0] collapses to
        nothing meaningful). UI treats an empty dict as "no range to show".
        """
        raw = obj.reference_ranges.get("default") if isinstance(obj.reference_ranges, dict) else None
        if not (isinstance(raw, list) and len(raw) == 2):
            return {}
        lo, hi = raw[0], raw[1]

        result: dict[str, list[float]] = {obj.default_unit: [float(lo), float(hi)]}
        for alt_unit in (obj.alternative_units or []):
            lo_alt = normalise(lo, obj.default_unit, alt_unit, obj.molecular_weight)
            hi_alt = normalise(hi, obj.default_unit, alt_unit, obj.molecular_weight)
            if lo_alt is None or hi_alt is None:
                # Graceful skip: if the converter can't translate this range
                # into this alt unit (e.g. missing MW), the UI just shows
                # no range for that unit rather than misleading numbers.
                continue
            result[alt_unit] = [round(lo_alt, 3), round(hi_alt, 3)]
        return result


class CatalogSerializer(serializers.Serializer):
    """Aggregated catalog payload for GET /catalog/."""
    categories = LabCategorySerializer(many=True)
    tests = LabTestTypeSerializer(many=True)


# ── Lab results ───────────────────────────────────────────────────────────────

class LabResultSerializer(serializers.ModelSerializer):
    test = serializers.SerializerMethodField()

    class Meta:
        model = LabResult
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
        )
        read_only_fields = fields

    def get_test(self, obj: LabResult) -> dict:
        t = obj.test_type
        return {
            "id": t.id,
            "abbreviation": t.abbreviation,
            "name": t.name,
            # category is nullable for auto-created rows (Phase 2c pivot).
            # Frontend treats "" as "no category — show under 'Other'".
            "category": t.category.key if t.category_id else "",
            "default_unit": t.default_unit,
            "value_type": t.value_type,
        }


# ── Shared validation + normalisation helpers (used by both create + update) ─

def _validate_value_fields(attrs: dict, test_type: LabTestType) -> None:
    """Enforce the value/qualitative/unit rules for a single lab result
    payload. Raises ValidationError on failure. Called by both the create
    and update serializers so the rules stay in one place (DRY)."""
    is_qualitative = test_type.value_type == ValueType.QUALITATIVE
    has_value = attrs.get("value") is not None
    has_qualitative = bool(attrs.get("value_qualitative"))

    if is_qualitative and not has_qualitative:
        raise serializers.ValidationError(
            {"value_qualitative": "Qualitative tests require a value_qualitative."}
        )
    if not is_qualitative and not has_value:
        raise serializers.ValidationError({"value": "Numeric tests require a value."})

    if not is_qualitative:
        source_unit = attrs.get("unit") or test_type.default_unit
        if not is_convertible(source_unit, test_type.default_unit, test_type.molecular_weight):
            raise serializers.ValidationError(
                {
                    "unit": (
                        f"Cannot convert {source_unit!r} to {test_type.default_unit!r}. "
                        "Use the test's default unit or a compatible one."
                    )
                }
            )


def _apply_normalised_fields(
    validated_data: dict,
    test_type: LabTestType,
    result: LabResult,
) -> None:
    """Populate value/unit/reference/date fields on `result` from validated
    input, applying unit normalisation and reference-range precedence
    (report wins, catalog fallback — §CQ2).

    Does NOT touch provenance fields (source, match_method, confidence) —
    those are set on create and left alone on update so a manually-edited
    FHIR-sourced result keeps its origin trail, with just the value changed.
    """
    is_qualitative = test_type.value_type == ValueType.QUALITATIVE
    source_value = validated_data.get("value")
    source_unit = (validated_data.get("unit") or test_type.default_unit).strip()

    if is_qualitative:
        result.value = None
        result.value_qualitative = validated_data.get("value_qualitative", "").strip()
        result.source_text = result.value_qualitative
    else:
        value = normalise(
            source_value,
            source_unit,
            test_type.default_unit,
            molecular_weight=test_type.molecular_weight,
        )
        if value is None:
            raise serializers.ValidationError(
                {"value": "Unit conversion failed. Contact support if this persists."}
            )
        result.value = value
        result.value_qualitative = ""
        result.source_text = str(source_value)

    result.source_unit = source_unit
    result.unit = test_type.default_unit

    # Reference range — report wins when provided, else catalog default
    report_min = validated_data.get("reference_min")
    report_max = validated_data.get("reference_max")
    if report_min is not None and report_max is not None:
        result.reference_min = normalise(
            report_min, source_unit, test_type.default_unit, test_type.molecular_weight
        )
        result.reference_max = normalise(
            report_max, source_unit, test_type.default_unit, test_type.molecular_weight
        )
        result.reference_source = ReferenceSource.REPORT
    else:
        catalog_min, catalog_max = test_type.default_range()
        result.reference_min = catalog_min
        result.reference_max = catalog_max
        result.reference_source = (
            ReferenceSource.CATALOG if catalog_min is not None else ReferenceSource.NONE
        )

    result.measured_at = validated_data.get("measured_at")


class LabResultCreateSerializer(serializers.Serializer):
    """
    Manual entry payload for POST /labs/results/. Accepts raw values + units
    and does the normalisation server-side. The input unit can be anything
    the catalog test supports (convertible to default_unit); if not, 400.

    Fields:
        test_type_id    : int (required) — catalog row to file the result under
        value           : float | null — for numeric tests
        value_qualitative : str | null — for qualitative tests
        unit            : str (optional) — defaults to the test's default_unit
        measured_at     : date (optional)
        reference_min   : float | null — optional, report-sourced
        reference_max   : float | null — optional, report-sourced
    """

    test_type_id = serializers.IntegerField()
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            test_type = LabTestType.objects.select_related("category").get(pk=attrs["test_type_id"])
        except LabTestType.DoesNotExist:
            raise serializers.ValidationError({"test_type_id": "Unknown test type."})
        _validate_value_fields(attrs, test_type)
        attrs["_test_type"] = test_type
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        test_type: LabTestType = validated_data["_test_type"]
        result = LabResult(
            user=request.user,
            test_type=test_type,
            match_method=MatchMethod.MANUAL,
            source="manual",
            confidence=1.0,
        )
        _apply_normalised_fields(validated_data, test_type, result)
        result.save()
        return result


class LabResultUpdateSerializer(serializers.Serializer):
    """
    Payload for PATCH /labs/results/{id}/. Accepts the same value/unit/date
    fields as create, EXCEPT test_type_id which is immutable — you can't
    turn a hemoglobin row into a creatinine row by editing it. Create a
    new row and delete the old one if that's what the user wants.

    Provenance fields (source, match_method, confidence) are NOT touched
    on update. A manually-edited document-extracted row keeps source=
    "document_extraction" but gets a fresh value. When upload lands in
    Phase 2b, we can decide whether an edit should bump confidence to 1.0
    (user has verified the value) — for now, leave it alone.
    """

    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        if not self.instance:
            raise serializers.ValidationError("Update serializer requires an instance.")
        _validate_value_fields(attrs, self.instance.test_type)
        return attrs

    def update(self, instance, validated_data):
        _apply_normalised_fields(validated_data, instance.test_type, instance)
        instance.save()
        return instance


# ── Lab uploads (Phase 2b) ────────────────────────────────────────────────────

class LabUploadFileSerializer(serializers.ModelSerializer):
    """Read-only nested representation of a file inside an upload response."""

    class Meta:
        model = LabUploadFile
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


class LabUploadSerializer(serializers.ModelSerializer):
    """Read payload for GET /api/v1/labs/uploads/{id}/ and create responses.

    Frontend polls this while status is pending/processing. Once the status
    flips to completed, parsed_results is populated (Phase 2c fills it in;
    Phase 2b's stub task leaves it as []).
    """

    files = LabUploadFileSerializer(many=True, read_only=True)

    class Meta:
        model = LabUpload
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

# Accepted extension fallback — used when the client sends an empty or unknown
# content_type header. Maps extension → canonical MIME type. Extension
# matching is case-insensitive.
_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".heic": "image/heic",
    ".heif": "image/heic",
}


def _sniff_mime(first_bytes: bytes) -> str | None:
    """Lightweight magic-byte sniff for the four file types we accept.
    Returns the canonical MIME type or None. Cheaper than python-magic and
    covers exactly what LAB_UPLOAD_ACCEPTED_MIME_TYPES allows.

    PDF:  first 4 bytes = "%PDF"
    PNG:  first 8 bytes = \\x89PNG\\r\\n\\x1a\\n
    JPEG: first 3 bytes = \\xff\\xd8\\xff
    HEIC: bytes 4..12 contain "ftypheic" / "ftypheix" / "ftypmif1" / "ftypmsf1"
    """
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


class LabUploadCreateSerializer(serializers.Serializer):
    """Multipart input for POST /api/v1/labs/uploads/.

    Request shape:
        files: File[]        (1..LAB_UPLOAD_MAX_FILES)
        lab_date: YYYY-MM-DD (optional)
        notes: string        (optional, max 2000 chars)

    Dedup (§9.2): within the same user, if the incoming request has exactly
    one file and its sha256 matches a LabUploadFile on a non-failed prior
    LabUpload, we return that prior LabUpload instead of creating a new one.
    Multi-file requests always create a new session — cheap dedup logic
    covers 95%+ of the "I tapped submit twice" case without scoring the
    multi-file Cartesian product.
    """

    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=settings.LAB_UPLOAD_MAX_FILES,
        help_text=f"1..{settings.LAB_UPLOAD_MAX_FILES} files, 10 MB each, 20 MB total.",
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

        for idx, f in enumerate(files):
            if f.size > max_file:
                raise serializers.ValidationError(
                    f"'{f.name}' is {_human_bytes(f.size)} (max {_human_bytes(max_file)} per file)."
                )
            total += f.size
            if total > max_total:
                raise serializers.ValidationError(
                    f"Total upload is {_human_bytes(total)} (max {_human_bytes(max_total)} per session)."
                )

            # Sniff magic bytes. The client's Content-Type is advisory; if the
            # sniff disagrees with an accepted type, reject. We read ONCE
            # here and reuse both hash + detected mime below.
            f.seek(0)
            head = f.read(12)
            f.seek(0)

            sniffed = _sniff_mime(head)
            ext_mime = _EXT_TO_MIME.get(_ext_of(f.name))
            # If we can't sniff and the extension isn't in our allowlist, reject.
            detected = sniffed or ext_mime
            if detected not in accepted:
                raise serializers.ValidationError(
                    f"'{f.name}': unsupported file type. We accept PDF, JPEG, PNG, HEIC."
                )

            # Hash the full stream. Reading the whole file once is fine for
            # 10MB caps; streaming chunked hashing is unnecessary complexity.
            import hashlib
            h = hashlib.sha256()
            for chunk in f.chunks():
                h.update(chunk)
            sha256 = h.hexdigest()
            f.seek(0)

            if sha256 in seen_hashes:
                raise serializers.ValidationError(
                    f"'{f.name}' appears twice in this upload. Remove one copy."
                )
            seen_hashes.add(sha256)

            annotated.append({
                "file": f,
                "original_filename": f.name,
                "mime_type": detected,
                "size_bytes": f.size,
                "file_order": idx,
                "sha256": sha256,
            })

        return annotated

    def create(self, validated_data):
        user = self.context["request"].user
        annotated = validated_data["files"]
        lab_date = validated_data.get("lab_date")
        notes = validated_data.get("notes", "")

        # ── Cross-session dedup (single-file case only) ──────────────────
        if len(annotated) == 1:
            hash_ = annotated[0]["sha256"]
            existing = (
                LabUpload.objects
                .filter(user=user, files__sha256=hash_)
                .exclude(status=LabUploadStatus.FAILED)
                .order_by("-created_at")
                .first()
            )
            if existing is not None:
                # Stamp sentinel so the view can return a different status code
                # (200 instead of 201) when we're returning an existing row.
                self.context["_dedup_hit"] = True
                return existing

        # ── Fresh session ────────────────────────────────────────────────
        upload = LabUpload.objects.create(
            user=user,
            lab_date=lab_date,
            notes=notes,
        )
        for row in annotated:
            LabUploadFile.objects.create(
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


# ── Commit (Phase 2d) ────────────────────────────────────────────────────────

# Duplicate detection threshold: two numeric values within this relative
# distance (|a-b| / max(|a|,|b|)) are treated as the "same" measurement.
# 1% matches design doc §12.4.
_DUPLICATE_RELATIVE_TOLERANCE = 0.01


def _is_duplicate_result(user, result: LabResult) -> bool:
    """Check if `result` (post-normalisation, unsaved) duplicates an existing
    LabResult for this user. Matches by:
      - same test_type
      - same measured_at (if both have a date; if either is None → not dup)
      - numeric: value within ±1% of the stored value
      - qualitative: exact value_qualitative match

    Returns True if the caller should SKIP saving this result.
    """
    if result.measured_at is None:
        return False  # undated rows never dedup — patient can commit as-is

    qs = LabResult.objects.filter(
        user=user,
        test_type=result.test_type,
        measured_at=result.measured_at,
    )
    if result.test_type.value_type == ValueType.QUALITATIVE:
        return qs.filter(value_qualitative=result.value_qualitative).exists()
    if result.value is None:
        return False
    for existing in qs.exclude(value__isnull=True).only("value"):
        denom = max(abs(existing.value), abs(result.value), 1e-9)
        if abs(existing.value - result.value) / denom <= _DUPLICATE_RELATIVE_TOLERANCE:
            return True
    return False


class _AcceptedRowSerializer(serializers.Serializer):
    """One row inside the commit payload. Mirrors LabResultCreateSerializer
    but adds `source_index` — a stable handle into the upload's parsed_results
    so we can pull provenance (match_method + confidence) from the right
    parsed row even after the client reorders or edits fields.
    """

    source_index = serializers.IntegerField(min_value=0)
    test_type_id = serializers.IntegerField()
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            test_type = LabTestType.objects.select_related("category").get(
                pk=attrs["test_type_id"]
            )
        except LabTestType.DoesNotExist:
            raise serializers.ValidationError({"test_type_id": "Unknown test type."})
        _validate_value_fields(attrs, test_type)
        attrs["_test_type"] = test_type
        return attrs


class LabUploadCommitSerializer(serializers.Serializer):
    """POST /api/v1/labs/uploads/{id}/commit/

    Request:
        {
          "accepted": [
            {
              "source_index": 0,
              "test_type_id": 42,
              "value": 12.5,
              "unit": "g/dL",
              "measured_at": "2026-03-15",
              "reference_min": 12.0,
              "reference_max": 15.5
            },
            ...
          ]
        }

    Response:
        { "saved_count": 5, "skipped_count": 1, "results": [LabResult...] }

    Behavior:
      - Upload must be status=completed (enforced at the view).
      - Each accepted row creates a LabResult with source='document_extraction'
        and the match_method + confidence pulled from the upload's
        parsed_results[source_index]. The client's edits to value/unit/date
        override what the LLM extracted; test_type_id can be re-selected.
      - Duplicate rows (same test + date + value ±1%) are skipped silently
        — the patient sees the count in the response.
      - All-or-nothing: any validation failure rolls back every row.

    Idempotency: committing the same upload twice creates duplicates if the
    parsed data changed between calls. If it didn't, the dup check catches
    everything the second time. Not full idempotency keys — YAGNI for now.
    """

    accepted = serializers.ListField(
        child=_AcceptedRowSerializer(),
        allow_empty=True,
    )

    def validate(self, attrs):
        # Cross-row check: every source_index must exist in parsed_results
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

        saved: list[LabResult] = []
        skipped = 0

        with transaction.atomic():
            for row in self.validated_data["accepted"]:
                test_type: LabTestType = row["_test_type"]
                parsed = parsed_results[row["source_index"]]

                result = LabResult(
                    user=user,
                    test_type=test_type,
                    upload=upload,
                    source="document_extraction",
                    match_method=parsed.get("match_method") or MatchMethod.LOINC,
                    confidence=float(parsed.get("confidence", 0.0) or 0.0),
                )
                _apply_normalised_fields(row, test_type, result)

                if _is_duplicate_result(user, result):
                    skipped += 1
                    continue

                result.save()
                saved.append(result)

        return {"saved": saved, "skipped": skipped}
