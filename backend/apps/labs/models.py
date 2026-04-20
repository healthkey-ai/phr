"""
Lab results domain models.

Architecture source: docs/patient-app-lab-upload-design.md §4.2.
Key decisions from the 2026-04-09 eng review baked in:
  - `source_text` / `source_unit` (renamed from raw_value / raw_unit for clarity)
  - `reference_source` tracks whether ranges came from the report or the catalog
  - `MatchMethod` enum is the single source of truth for matching strategy
  - User deletion cascades through LabUpload + LabResult (§9.5)
  - Audit log references are pseudonymised via post_delete signal

Phase 2a implements: LabCategory, LabTestType, LabResult.
Phase 2b adds: LabUpload, LabUploadFile.
"""
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def _lab_upload_path(instance, filename):
    """Store uploaded files under MEDIA_ROOT/lab-uploads/YYYY/MM/<uuid><ext>.

    We replace the patient's filename with a UUID to prevent PII leaks through
    URLs (e.g. "sarah_johnson_bcma_2026.pdf"). The original filename is kept
    on LabUploadFile.original_filename for display.
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower() if ext else ""
    now = timezone.now()
    return f"lab-uploads/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


class MatchMethod(models.TextChoices):
    """How a LabResult was tied to its LabTestType. Referenced by serializers,
    views, matching.py, tests, and the frontend type definitions.

    Phase 2c design pivot: tiered alias/fuzzy matching is GONE. The LOINC code
    (§7 Tier 0a) is the identity; if the LLM doesn't return a usable LOINC, we
    fall back to normalized-name grouping (§7 step 3). The legacy values below
    are retained so old rows (if any exist) still validate — new code only
    produces LOINC / NAME_FALLBACK / MANUAL / UNMATCHED.
    """

    LOINC = "loinc", "LOINC direct"
    NAME_FALLBACK = "name_fallback", "Name fallback (no LOINC)"
    MANUAL = "manual", "Patient manually matched"
    UNMATCHED = "unmatched", "Unmatched"
    # Legacy (Phase 2a catalog matching, never produced in 2c+). Kept to not
    # break existing rows in dev databases.
    EXACT_ALIAS = "exact_alias", "Exact alias match (legacy)"
    FUZZY = "fuzzy", "Fuzzy match (legacy)"
    DISAMBIGUATION = "disambiguation", "Disambiguation rule (legacy)"


class ReferenceSource(models.TextChoices):
    """Where the reference range on a LabResult came from (§CQ2)."""

    REPORT = "report", "From report"
    CATALOG = "catalog", "Catalog default"
    NONE = "none", "No range"


class ValueType(models.TextChoices):
    NUMERIC = "numeric", "Numeric"
    QUALITATIVE = "qualitative", "Qualitative"
    RATIO = "ratio", "Ratio"


class LabCategory(models.Model):
    """Groups tests for display. Seeded via fixture, never user-edited."""

    key = models.CharField(max_length=32, unique=True)  # "cbc" / "liver" / "myeloma"
    name = models.CharField(max_length=64)              # "Complete Blood Count"
    display_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "labs_labcategory"
        ordering = ["display_order", "name"]
        verbose_name_plural = "lab categories"

    def __str__(self):
        return self.name


class LabTestType(models.Model):
    """Test identity + display metadata. Rows are either preloaded (see
    `fixtures/lab_catalog.json` for the curated ~37) or auto-created on first
    sight by `matching.resolve_test_identity` when a patient upload mentions
    a new test.

    Phase 2c pivot:
      - `aliases` dropped — matching no longer name-based (§7 + §1 non-goals)
      - `loinc_code` is the primary identity. Partial-unique when non-empty;
        the empty string is allowed for no-LOINC fallback rows and multiple
        such rows coexist keyed by `name_normalized` instead
      - `name_normalized` stored alongside for the no-LOINC fallback lookup
        (NFKD + casefold + punctuation strip). Populated in `save()`
      - `category` + `display_order` + `reference_ranges` + `molecular_weight`
        are optional curation fields, populated from `lab_catalog.json` for
        preloaded rows and left default for auto-created rows
    """

    category = models.ForeignKey(
        LabCategory,
        on_delete=models.PROTECT,
        related_name="tests",
        null=True,
        blank=True,
    )
    abbreviation = models.CharField(max_length=64, unique=True)  # "hgb"; for auto-created rows, slug of normalized name
    name = models.CharField(max_length=128)                      # "Hemoglobin"
    name_normalized = models.CharField(
        max_length=128,
        db_index=True,
        blank=True,
        default="",
        help_text="NFKD + casefold + punctuation strip of `name`. Used by "
                  "matching.resolve_test_identity to group no-LOINC rows. "
                  "Populated in save().",
    )
    loinc_code = models.CharField(max_length=16, db_index=True, blank=True, default="")
    default_unit = models.CharField(max_length=32)               # "g/dL" — canonical storage unit
    alternative_units = models.JSONField(default=list, blank=True)
    """Other units the patient may enter (e.g. ["g/L"] for hemoglobin in UK/EU).
    Does NOT include default_unit. unit_converter.normalise() handles the
    conversion to default_unit on save."""
    sample_values = models.JSONField(default=dict, blank=True)
    """Realistic example value per unit, rendered as the placeholder in the
    manual entry form so the patient sees the expected magnitude for the
    currently selected unit.

    Shape: {"<unit_string>": "<display_value>", ...}
    Example (hemoglobin): {"g/dL": "14.0", "g/L": "140"}

    Keys should cover default_unit + every alternative_unit. Values are strings
    (not floats) so they render verbatim. Empty dict is fine for qualitative
    tests."""
    reference_ranges = models.JSONField(default=dict, blank=True)  # { "default": [12.0, 15.5] }
    value_type = models.CharField(
        max_length=16,
        choices=ValueType.choices,
        default=ValueType.NUMERIC,
    )
    molecular_weight = models.FloatField(
        null=True,
        blank=True,
        help_text="Molecular weight in g/mol, for molar↔mass conversions (§8.2).",
    )
    display_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "labs_labtesttype"
        ordering = ["category__display_order", "display_order", "name"]
        indexes = [
            models.Index(fields=["loinc_code"]),
            models.Index(fields=["name_normalized"]),
        ]
        constraints = [
            # Partial unique: enforce loinc_code uniqueness ONLY when non-empty.
            # No-LOINC rows (loinc_code="") coexist, keyed by name_normalized.
            models.UniqueConstraint(
                fields=["loinc_code"],
                condition=models.Q(loinc_code__gt=""),
                name="uniq_labs_labtesttype_loinc_code_when_set",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    def default_range(self) -> tuple[float | None, float | None]:
        """Return (min, max) from reference_ranges['default'], or (None, None)."""
        default = self.reference_ranges.get("default") if isinstance(self.reference_ranges, dict) else None
        if isinstance(default, list) and len(default) == 2:
            return (default[0], default[1])
        return (None, None)

    def save(self, *args, **kwargs):
        # Keep name_normalized in sync with name. Lazy-import to avoid circular
        # dep: matching imports models.
        from .matching import normalize_name
        self.name_normalized = normalize_name(self.name)
        super().save(*args, **kwargs)


class LabResult(models.Model):
    """Single numeric or qualitative lab value, normalised to test_type.default_unit.

    USER DELETION POLICY (per eng review §A2):
      - on_delete=CASCADE wipes LabResult when the user deletes their account.
      - Audit log entries referencing deleted rows are pseudonymised via a
        post_delete signal: actor_id → NULL, resource_id → NULL.
      - No soft-delete, no de-identified retention for analytics.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lab_results",
    )
    test_type = models.ForeignKey(
        LabTestType,
        on_delete=models.PROTECT,
        related_name="results",
    )
    # Null for manual entries; set when a result was extracted from an upload.
    # SET_NULL so deleting an upload preserves its derived LabResults — the
    # patient's committed data outlives the source file.
    upload = models.ForeignKey(
        "LabUpload",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results",
    )

    # Numeric result (normalised to test_type.default_unit)
    value = models.FloatField(null=True, blank=True)
    value_qualitative = models.CharField(max_length=32, blank=True, default="")
    unit = models.CharField(max_length=32)

    # Verbatim from source (audit trail — §CQ1)
    source_text = models.CharField(max_length=64)
    source_unit = models.CharField(max_length=32)

    # Reference range (normalised)
    reference_min = models.FloatField(null=True, blank=True)
    reference_max = models.FloatField(null=True, blank=True)
    reference_source = models.CharField(
        max_length=8,
        choices=ReferenceSource.choices,
        default=ReferenceSource.NONE,
    )

    # Provenance
    match_method = models.CharField(
        max_length=16,
        choices=MatchMethod.choices,
        default=MatchMethod.MANUAL,
    )
    source = models.CharField(
        max_length=32,
        choices=[
            ("manual", "Manual entry"),
            ("document_extraction", "Document extraction"),
            ("fhir", "FHIR sync"),
        ],
        default="manual",
    )
    confidence = models.FloatField(default=1.0)  # 0..1; manual = 1.0

    status = models.CharField(
        max_length=16,
        choices=[
            ("in_range", "In range"),
            ("below", "Below"),
            ("above", "Above"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )

    measured_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "labs_labresult"
        ordering = ["-measured_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "test_type", "-measured_at"]),
        ]

    def __str__(self):
        val = self.value if self.value is not None else self.value_qualitative
        return f"{self.test_type.abbreviation}={val} {self.unit} @ {self.measured_at}"

    def recompute_status(self) -> None:
        """Derive status from value + reference range. Ignores qualitative tests."""
        if self.value is None or self.reference_min is None or self.reference_max is None:
            self.status = "unknown"
            return
        if self.value < self.reference_min:
            self.status = "below"
        elif self.value > self.reference_max:
            self.status = "above"
        else:
            self.status = "in_range"

    def save(self, *args, **kwargs):
        # Unit is always the canonical default_unit for the test type
        if self.test_type_id and not self.unit:
            self.unit = self.test_type.default_unit
        self.recompute_status()
        super().save(*args, **kwargs)


class LabUploadStatus(models.TextChoices):
    """Status lifecycle for a LabUpload session.

    pending   → row created, files saved, Celery task enqueued. The API
                returns this state on the create response.
    processing → worker picked up the task and started extraction. The
                 review UI shows the "Reading your report…" progress screen.
    completed → extraction finished (may be empty). parsed_results is
                populated. Review UI can render.
    failed    → extraction failed — error_message explains. UI offers retry.

    Phase 2b only uses pending/processing/completed (the stub task flips to
    completed immediately with empty parsed_results). Phase 2c introduces
    real extraction and the failed path.
    """

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class LabUpload(models.Model):
    """One upload session. Can contain 1–10 files (design doc §5.2).

    Lifecycle is owned by the Celery task `process_lab_upload`. Phase 2b ships
    a stub that completes immediately with an empty parsed_results; Phase 2c
    fills in real LLM extraction against the same model.

    Dedup: the first file's sha256 is the session's content identity. If a
    user re-uploads a file with a matching sha256 that's part of a still-valid
    prior LabUpload (not status=failed), the API returns the existing session
    instead of creating a new one. See `serializers.LabUploadCreateSerializer`.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lab_uploads",
    )
    status = models.CharField(
        max_length=16,
        choices=LabUploadStatus.choices,
        default=LabUploadStatus.PENDING,
        db_index=True,
    )

    # Which LLM produced the extraction. Phase 2c sets this to "claude";
    # Phase 2b stub leaves it empty.
    provider = models.CharField(max_length=32, blank=True, default="")

    # Patient-supplied context
    lab_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    # Extraction output. Pre-match, raw LLM results; Phase 2b leaves it [].
    parsed_results = models.JSONField(default=list, blank=True)

    # Job tracking
    celery_task_id = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "labs_labupload"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"LabUpload<{self.id} user={self.user_id} status={self.status}>"

    def mark_processing(self) -> None:
        self.status = LabUploadStatus.PROCESSING
        self.save(update_fields=["status"])

    def mark_completed(self, parsed_results: list | None = None) -> None:
        self.status = LabUploadStatus.COMPLETED
        self.parsed_results = parsed_results or []
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "parsed_results", "completed_at"])

    def mark_failed(self, message: str) -> None:
        self.status = LabUploadStatus.FAILED
        self.error_message = message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


class LabUploadFile(models.Model):
    """One file within a LabUpload. Ordered for multi-page/multi-file processing.

    Dedup key is `(user, sha256)` — same user uploading the same bytes
    returns the existing upload. Across users, identical bytes are stored
    separately: there's no cross-user sharing, even for identical reports.
    """

    upload = models.ForeignKey(
        LabUpload,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to=_lab_upload_path)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    file_order = models.PositiveSmallIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "labs_labuploadfile"
        ordering = ["upload_id", "file_order"]
        indexes = [
            # Dedup lookup uses (user via upload) + sha256. Postgres can
            # satisfy the join via this index + labs_labupload's PK.
            models.Index(fields=["sha256"]),
        ]

    def __str__(self):
        return f"LabUploadFile<{self.id} upload={self.upload_id} {self.original_filename}>"
