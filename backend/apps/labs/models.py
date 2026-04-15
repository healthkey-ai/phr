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
from django.conf import settings
from django.db import models
from django.utils import timezone


class MatchMethod(models.TextChoices):
    """How a LabResult was tied to its LabTestType. Referenced by serializers,
    views, matching.py (Phase 2c), tests, and the frontend type definitions.

    Resolved in eng review §CQ3 — DRY across the codebase."""

    LOINC = "loinc", "LOINC direct"
    EXACT_ALIAS = "exact_alias", "Exact alias match"
    FUZZY = "fuzzy", "Fuzzy match"
    DISAMBIGUATION = "disambiguation", "Disambiguation rule"
    MANUAL = "manual", "Patient manually matched"
    UNMATCHED = "unmatched", "Unmatched"


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
    """Canonical test definition. Seeded via fixture, never user-edited.

    Adding a test is a migration, not an API call. See
    `apps/labs/fixtures/lab_catalog.json` for the current catalog.
    """

    category = models.ForeignKey(
        LabCategory,
        on_delete=models.PROTECT,
        related_name="tests",
    )
    abbreviation = models.CharField(max_length=32, unique=True)  # "hgb"
    name = models.CharField(max_length=128)                      # "Hemoglobin"
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
    aliases = models.JSONField(default=list, blank=True)         # ["HGB", "Hb", "haemoglobin"]
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
        ]

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

    def default_range(self) -> tuple[float | None, float | None]:
        """Return (min, max) from reference_ranges['default'], or (None, None)."""
        default = self.reference_ranges.get("default") if isinstance(self.reference_ranges, dict) else None
        if isinstance(default, list) and len(default) == 2:
            return (default[0], default[1])
        return (None, None)


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
    # Phase 2b: FK to LabUpload. Optional for manual entry.
    # Left as a CharField placeholder here to avoid the migration coupling in Phase 2a.
    # Will be replaced by a real ForeignKey in a Phase 2b migration.
    upload_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

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
