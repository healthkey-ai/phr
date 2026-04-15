"""
PatientInfo — flat denormalized patient record table.

Per architecture doc §2.3: clinical fields live in `details` JSONB to avoid
a migration per new disease-specific field. JSON Schema validation enforces
structure on write.

Source of truth: docs/patient-app-requirements.md §2 (data collection schema).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class PatientInfo(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_info",
    )

    # ─── Demographics (§2.1) ───
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True, default="")
    ethnicity = models.JSONField(default=list, blank=True)  # multiselect → list of strings
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)  # calculated server-side
    country = models.CharField(max_length=3, blank=True, default="")  # ISO 3166-1 alpha-3
    postal_code = models.CharField(max_length=16, blank=True, default="")
    geo_lat = models.FloatField(null=True, blank=True)
    geo_long = models.FloatField(null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    insurance_status = models.CharField(max_length=64, blank=True, default="")
    employment_status = models.CharField(max_length=64, blank=True, default="")

    # ─── Cancer/disease selector (§2.2) ───
    disease = models.CharField(max_length=64, blank=True, default="")

    # ─── Conditions, lifestyle, family, lab values, disease profile (§2.2-2.7) ───
    # Stored as JSONB to allow disease-conditional schema flexibility.
    # See docs/patient-app-architecture.md §4.4 for the schema validator.
    details = models.JSONField(default=dict, blank=True)

    # ─── Completeness (§4.1.2) ───
    completeness_score = models.FloatField(default=0.0)
    completeness_by_category = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_profile_patientinfo"

    def __str__(self):
        return f"PatientInfo({self.user.email})"

    def recompute_calculated_fields(self):
        """
        Recompute server-side calculated fields per docs/patient-app-architecture.md
        Appendix B. Run on every save() that touches relevant inputs.
        """
        # BMI from height + weight
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / 100.0
            self.bmi = round(self.weight_kg / (height_m * height_m), 2)
        else:
            self.bmi = None

    def recompute_completeness(self):
        """
        Compute completeness % per category and overall.
        Categories: demographics, conditions, lifestyle, family, labs, disease_profile.
        """
        cat_scores = {
            "demographics": self._completeness_demographics(),
            "conditions": self._completeness_conditions(),
            "lifestyle": self._completeness_lifestyle(),
            "family": self._completeness_family(),
            "labs": self._completeness_labs(),
        }
        if self.disease:
            cat_scores["disease_profile"] = self._completeness_disease_profile()

        self.completeness_by_category = cat_scores
        self.completeness_score = round(sum(cat_scores.values()) / len(cat_scores), 1)

    # ─── Per-category completeness helpers ───

    def _completeness_demographics(self) -> float:
        required = [
            self.first_name, self.last_name, self.dob, self.gender,
            self.height_cm, self.weight_kg, self.country, self.postal_code,
        ]
        filled = sum(1 for v in required if v not in (None, "", []))
        return round(filled / len(required) * 100, 1)

    def _completeness_conditions(self) -> float:
        conditions = self.details.get("conditions", []) or []
        allergies = self.details.get("drugAllergies", []) or []
        meds = self.details.get("currentMedications", []) or []
        slots = [bool(conditions), bool(allergies), bool(meds)]
        return round(sum(slots) / len(slots) * 100, 1)

    def _completeness_lifestyle(self) -> float:
        keys = ["smokingStatus", "alcoholFrequency", "exerciseLevel", "dietType", "occupation"]
        filled = sum(1 for k in keys if self.details.get(k))
        return round(filled / len(keys) * 100, 1)

    def _completeness_family(self) -> float:
        family = self.details.get("familyHistory", {}) or {}
        return 100.0 if family else 0.0

    def _completeness_labs(self) -> float:
        lab_keys = [
            "hemoglobinLevel", "whiteBloodCellCount", "plateletCount",
            "serumCreatinineLevel", "liverEnzymeLevelsAlt",
        ]
        filled = sum(1 for k in lab_keys if self.details.get(k) is not None)
        return round(filled / len(lab_keys) * 100, 1)

    def _completeness_disease_profile(self) -> float:
        if not self.disease:
            return 0.0
        keys = ["stage", "ecogPerformanceStatus"]
        filled = sum(1 for k in keys if self.details.get(k) not in (None, ""))
        return round(filled / len(keys) * 100, 1)

    def save(self, *args, **kwargs):
        self.recompute_calculated_fields()
        self.recompute_completeness()
        super().save(*args, **kwargs)


class PatientInfoVersion(models.Model):
    """
    Immutable change-tracking record. One row per PATCH.
    Per architecture §2.3 and HIPAA §164.312 audit requirements.
    """

    SOURCE_CHOICES = [
        ("manual", "Manual entry"),
        ("fhir", "FHIR sync"),
        ("document_extraction", "Document AI extraction"),
        ("caregiver", "Caregiver edit"),
    ]

    patient_info = models.ForeignKey(
        PatientInfo, on_delete=models.CASCADE, related_name="versions"
    )
    changed_fields = models.JSONField(default=dict)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default="manual")
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "patient_profile_patientinfoversion"
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["patient_info", "-timestamp"])]
