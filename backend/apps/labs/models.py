"""
Lab results domain models — v2.

Key changes from v1:
  - LabTestType → LabTestEntry (loinc_code string replaced by FK to LoincEntry)
  - LabResult → LabValue
  - LabUpload → UploadJob
  - LabUploadFile → UploadFile
  - LabUploadStatus → UploadStatus
  - LabCategory removed — category comes from LoincEntry.category
  - reference_ranges removed from LabTestEntry — ranges come exclusively
    from user-supplied data (uploaded reports or manual entry)
  - New models: LoincEntry, LoincAlias
  - MatchMethod gains ALIAS_EXACT for Tier 1 bag-of-words matches
"""
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def _lab_upload_path(instance, filename):
    """Store uploaded files under MEDIA_ROOT/lab-uploads/YYYY/MM/<uuid><ext>."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower() if ext else ""
    now = timezone.now()
    return f"lab-uploads/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


class MatchMethod(models.TextChoices):
    """How a LabValue was tied to its LabTestEntry."""

    LOINC = "loinc", "LOINC direct (Tier 0)"
    ALIAS_EXACT = "alias_exact", "Alias exact match (Tier 1)"
    NAME_FALLBACK = "name_fallback", "Name fallback (stub)"
    MANUAL = "manual", "Patient manually matched"
    UNMATCHED = "unmatched", "Unmatched"


class ReferenceSource(models.TextChoices):
    """Where the reference range on a LabValue came from."""

    REPORT = "report", "From report"
    NONE = "none", "No range"


class ValueType(models.TextChoices):
    NUMERIC = "numeric", "Numeric"
    QUALITATIVE = "qualitative", "Qualitative"
    RATIO = "ratio", "Ratio"


# ── LOINC reference data ────────────────────────────────────────────────────


class LoincEntry(models.Model):
    """Canonical LOINC code reference. One row per LOINC code (~60k for
    ACTIVE, CLASSTYPE=1). Loaded from LOINC CSV via loinc_reset management
    command."""

    code = models.CharField(max_length=16, unique=True, db_index=True)
    component = models.CharField(max_length=128, blank=True, default="")
    short_name = models.CharField(max_length=128, blank=True, default="")
    long_name = models.CharField(max_length=256, blank=True, default="")
    system = models.CharField(max_length=64, blank=True, default="")
    default_unit = models.CharField(max_length=32, blank=True, default="")
    unit_family = models.CharField(max_length=32, blank=True, default="")
    category = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=16, default="ACTIVE")
    value_type = models.CharField(
        max_length=16,
        choices=ValueType.choices,
        default=ValueType.NUMERIC,
    )

    class Meta:
        db_table = "labs_loincentry"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.short_name}"


class LoincAlias(models.Model):
    """Alias for a LOINC code. Powers the Tier 1 bag-of-words index."""

    loinc_entry = models.ForeignKey(
        LoincEntry,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    text = models.CharField(max_length=256)
    text_normalized = models.CharField(max_length=256, db_index=True)
    source = models.CharField(
        max_length=32,
        choices=[
            ("csv_extraction", "CSV extraction"),
            ("alias_rule", "Alias rule"),
            ("curated", "Curated"),
        ],
        default="csv_extraction",
    )

    class Meta:
        db_table = "labs_loincalias"
        indexes = [
            models.Index(fields=["text_normalized"]),
        ]

    def __str__(self):
        return f"{self.text} → {self.loinc_entry.code}"


# ── Test identity ───────────────────────────────────────────────────────────


class LabTestEntry(models.Model):
    """Test identity + display metadata. Rows are either preloaded from the
    fixture or auto-created on first sight by the matcher.

    Category comes from loinc_entry.category (no separate LabCategory model).
    Reference ranges are NOT stored here — they come exclusively from
    user-supplied data on LabValue.
    """

    loinc_entry = models.ForeignKey(
        LoincEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_entries",
    )
    abbreviation = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    name_normalized = models.CharField(
        max_length=128,
        db_index=True,
        blank=True,
        default="",
    )
    default_unit = models.CharField(max_length=32, blank=True, default="")
    alternative_units = models.JSONField(default=list, blank=True)
    sample_values = models.JSONField(default=dict, blank=True)
    value_type = models.CharField(
        max_length=16,
        choices=ValueType.choices,
        default=ValueType.NUMERIC,
    )
    molecular_weight = models.FloatField(null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        db_table = "labs_labtestentry"
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["name_normalized"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    @property
    def category(self):
        """Category string from the linked LoincEntry, or empty string."""
        if self.loinc_entry_id:
            return self.loinc_entry.category
        return ""

    def save(self, *args, **kwargs):
        from .matching import normalize_name
        self.name_normalized = normalize_name(self.name)
        super().save(*args, **kwargs)


# ── Lab values ──────────────────────────────────────────────────────────────


class LabValue(models.Model):
    """Single numeric or qualitative lab value, normalised to
    test_entry.default_unit.

    Reference ranges come exclusively from report extraction or user manual
    entry — never from hardcoded catalog defaults.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lab_values",
    )
    test_entry = models.ForeignKey(
        LabTestEntry,
        on_delete=models.PROTECT,
        related_name="values",
    )
    loinc_entry = models.ForeignKey(
        LoincEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_values",
    )
    upload = models.ForeignKey(
        "UploadJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="values",
    )

    value = models.FloatField(null=True, blank=True)
    value_qualitative = models.CharField(max_length=32, blank=True, default="")
    unit = models.CharField(max_length=32)

    source_text = models.CharField(max_length=64)
    source_unit = models.CharField(max_length=32)

    reference_min = models.FloatField(null=True, blank=True)
    reference_max = models.FloatField(null=True, blank=True)
    reference_text = models.TextField(blank=True, default="")
    reference_source = models.CharField(
        max_length=8,
        choices=ReferenceSource.choices,
        default=ReferenceSource.NONE,
    )

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
    confidence = models.FloatField(default=1.0)

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
        db_table = "labs_labvalue"
        ordering = ["-measured_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "test_entry", "-measured_at"]),
        ]

    def __str__(self):
        val = self.value if self.value is not None else self.value_qualitative
        return f"{self.test_entry.abbreviation}={val} {self.unit} @ {self.measured_at}"

    def recompute_status(self) -> None:
        if self.value is None or (self.reference_min is None and self.reference_max is None):
            self.status = "unknown"
            return
        if self.reference_min is not None and self.value < self.reference_min:
            self.status = "below"
        elif self.reference_max is not None and self.value > self.reference_max:
            self.status = "above"
        else:
            self.status = "in_range"

    def save(self, *args, **kwargs):
        if self.test_entry_id and not self.unit:
            self.unit = self.test_entry.default_unit
        self.recompute_status()
        super().save(*args, **kwargs)


# ── Uploads ─────────────────────────────────────────────────────────────────


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class UploadJob(models.Model):
    """One upload session. Can contain 1–10 files."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upload_jobs",
    )
    status = models.CharField(
        max_length=16,
        choices=UploadStatus.choices,
        default=UploadStatus.PENDING,
        db_index=True,
    )
    provider = models.CharField(max_length=32, blank=True, default="")
    lab_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    raw_llm_response = models.JSONField(default=list, blank=True)
    parsed_results = models.JSONField(default=list, blank=True)
    celery_task_id = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "labs_uploadjob"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"UploadJob<{self.id} user={self.user_id} status={self.status}>"

    def mark_processing(self) -> None:
        self.status = UploadStatus.PROCESSING
        self.save(update_fields=["status"])

    def mark_completed(self, parsed_results: list | None = None) -> None:
        self.status = UploadStatus.COMPLETED
        self.parsed_results = parsed_results or []
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "parsed_results", "completed_at"])

    def mark_failed(self, message: str) -> None:
        self.status = UploadStatus.FAILED
        self.error_message = message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


class UploadFile(models.Model):
    """One file within an UploadJob."""

    upload = models.ForeignKey(
        UploadJob,
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
        db_table = "labs_uploadfile"
        ordering = ["upload_id", "file_order"]
        indexes = [
            models.Index(fields=["sha256"]),
        ]

    def __str__(self):
        return f"UploadFile<{self.id} upload={self.upload_id} {self.original_filename}>"
