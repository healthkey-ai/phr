from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
    """Operational patient data for the HealthKey portal.

    Stores onboarding state, preferences, and disease-conditional
    fields as JSONB. Clinical records live in dedicated services
    (e.g. hk-labs) keyed to the same account.
    """

    ONBOARDING_STEPS = [
        ("welcome", "Welcome"),
        ("demographics", "Demographics"),
        ("conditions", "Conditions"),
        ("lifestyle", "Lifestyle"),
        ("family", "Family History"),
        ("summary", "Summary"),
        ("complete", "Complete"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    onboarding_step = models.CharField(
        max_length=20,
        choices=ONBOARDING_STEPS,
        default="welcome",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Disease-conditional fields and preferences",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_profile"

    def __str__(self):
        return f"Profile for {self.user.email}"
