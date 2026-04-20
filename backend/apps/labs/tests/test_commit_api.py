"""
Phase 2d: commit + retry endpoint tests.

Scope:
  POST /api/v1/labs/uploads/{id}/commit/
    - happy path: accepted rows become LabResult objects
    - patient edits (value, unit, date) override LLM output
    - test_type_id override swaps the row to a different test
    - duplicate detection skips existing (test + date + value ±1%)
    - rejecting a row (omitting from accepted[]) doesn't create it
    - non-completed upload returns 400
    - other user's upload returns 404
    - invalid source_index rejected
    - empty accepted[] is valid (no-op, 0 saved)

  POST /api/v1/labs/uploads/{id}/extract/
    - resets status + re-enqueues task
    - other user's upload returns 404
"""
from datetime import date
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.labs.models import (
    LabResult,
    LabTestType,
    LabUpload,
    LabUploadFile,
    LabUploadStatus,
)


@pytest.fixture(autouse=True)
def _force_celery_eager(settings):
    """Same reason as in test_uploads_api.py / test_pipeline.py: tests assume
    `.delay()` runs the task inline; a dev .env with CELERY_BROKER_URL set
    to real Redis would break retry-endpoint tests without this pin."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def catalog(db):
    call_command("loaddata", "lab_catalog.json", app_label="labs", verbosity=0)


@pytest.fixture
def user(db):
    return User.objects.create_user(email="sarah@example.com", password="Strong-Pass-123!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="intruder@example.com", password="Strong-Pass-123!")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def other_client(other_user):
    c = APIClient()
    c.force_authenticate(user=other_user)
    return c


def _make_completed_upload(user, catalog, parsed_results=None):
    """Build a completed LabUpload with parsed_results mimicking the Phase 2c
    pipeline output. No real files — we're testing commit, not extraction."""
    hgb = LabTestType.objects.get(abbreviation="hgb")
    wbc = LabTestType.objects.get(abbreviation="wbc")

    default_parsed = [
        {
            "source_index": 0,
            "raw_name": "Hemoglobin",
            "raw_loinc_code": "718-7",
            "raw_unit": "g/dL",
            "value": "12.5",
            "unit": "g/dL",
            "reference_min": 12.0,
            "reference_max": 15.5,
            "measured_date": "2026-03-15",
            "page": 0,
            "confidence": 0.95,
            "matched_test_id": hgb.id,
            "matched_test_abbreviation": "hgb",
            "matched_test_name": "Hemoglobin",
            "match_method": "loinc",
            "accepted": None,
        },
        {
            "source_index": 1,
            "raw_name": "WBC",
            "raw_loinc_code": "6690-2",
            "raw_unit": "10^3/uL",
            "value": "7.2",
            "unit": "10^3/uL",
            "reference_min": 4.5,
            "reference_max": 11.0,
            "measured_date": "2026-03-15",
            "page": 0,
            "confidence": 0.92,
            "matched_test_id": wbc.id,
            "matched_test_abbreviation": "wbc",
            "matched_test_name": "White blood cell count",
            "match_method": "loinc",
            "accepted": None,
        },
    ]

    upload = LabUpload.objects.create(
        user=user,
        status=LabUploadStatus.COMPLETED,
        lab_date=date(2026, 3, 15),
        parsed_results=parsed_results if parsed_results is not None else default_parsed,
    )
    return upload


# ── Commit happy path ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCommitHappyPath:
    def test_accepts_both_rows_creates_two_results(self, client, user, catalog):
        upload = _make_completed_upload(user, catalog)
        hgb = LabTestType.objects.get(abbreviation="hgb")
        wbc = LabTestType.objects.get(abbreviation="wbc")

        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL", "measured_at": "2026-03-15",
                     "reference_min": 12.0, "reference_max": 15.5},
                    {"source_index": 1, "test_type_id": wbc.id, "value": 7.2,
                     "unit": "10^3/uL", "measured_at": "2026-03-15",
                     "reference_min": 4.5, "reference_max": 11.0},
                ]
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["saved_count"] == 2
        assert body["skipped_count"] == 0
        assert len(body["results"]) == 2

        # Verify DB state
        assert LabResult.objects.filter(user=user).count() == 2
        hgb_result = LabResult.objects.get(user=user, test_type=hgb)
        assert hgb_result.value == 12.5
        assert hgb_result.source == "document_extraction"
        assert hgb_result.match_method == "loinc"
        assert hgb_result.confidence == 0.95
        assert hgb_result.upload_id == upload.id

    def test_reject_a_row_by_omitting_it(self, client, user, catalog):
        """Only include one source_index in accepted → only one LabResult."""
        upload = _make_completed_upload(user, catalog)
        hgb = LabTestType.objects.get(abbreviation="hgb")

        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["saved_count"] == 1
        assert LabResult.objects.count() == 1

    def test_empty_accepted_is_valid_noop(self, client, user, catalog):
        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={"accepted": []},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["saved_count"] == 0
        assert LabResult.objects.count() == 0

    def test_patient_edit_overrides_llm_value(self, client, user, catalog):
        """LLM returned value=12.5, patient edits to 13.0 before commit."""
        upload = _make_completed_upload(user, catalog)
        hgb = LabTestType.objects.get(abbreviation="hgb")

        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 13.0,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.status_code == 200
        result = LabResult.objects.get(user=user)
        assert result.value == 13.0  # patient's edit, not the LLM's 12.5

    def test_test_type_id_override_swaps_test(self, client, user, catalog):
        """Patient re-selects a different test type in review. Commit respects
        the override, not the matched_test_id from parsed_results."""
        upload = _make_completed_upload(user, catalog)
        # parsed_results[0] was for hgb; patient re-tags it as ferritin
        # (an auto-create test type not in lab_catalog.json)
        from apps.labs.matching import resolve_test_identity
        ferritin, _ = resolve_test_identity("Ferritin", "2276-4", "ng/mL")

        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": ferritin.id, "value": 150,
                     "unit": "ng/mL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.status_code == 200
        result = LabResult.objects.get(user=user)
        assert result.test_type_id == ferritin.id


# ── Duplicate detection ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDuplicateDetection:
    def test_exact_duplicate_skipped(self, client, user, catalog):
        """An existing LabResult at the same date + exact same value gets
        skipped. saved_count + skipped_count reflect reality."""
        hgb = LabTestType.objects.get(abbreviation="hgb")
        LabResult.objects.create(
            user=user,
            test_type=hgb,
            value=12.5,
            unit="g/dL",
            source_text="12.5",
            source_unit="g/dL",
            source="manual",
            measured_at=date(2026, 3, 15),
        )

        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["saved_count"] == 0
        assert body["skipped_count"] == 1

    def test_value_within_1_percent_skipped(self, client, user, catalog):
        """12.55 vs 12.50 = 0.4% diff — within 1% tolerance, skipped."""
        hgb = LabTestType.objects.get(abbreviation="hgb")
        LabResult.objects.create(
            user=user, test_type=hgb, value=12.50, unit="g/dL",
            source_text="12.50", source_unit="g/dL", source="manual",
            measured_at=date(2026, 3, 15),
        )

        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.55,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.json()["skipped_count"] == 1

    def test_value_outside_1_percent_not_skipped(self, client, user, catalog):
        """12.8 vs 12.5 = 2.4% — outside tolerance, saved."""
        hgb = LabTestType.objects.get(abbreviation="hgb")
        LabResult.objects.create(
            user=user, test_type=hgb, value=12.5, unit="g/dL",
            source_text="12.5", source_unit="g/dL", source="manual",
            measured_at=date(2026, 3, 15),
        )

        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.8,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        body = response.json()
        assert body["saved_count"] == 1
        assert body["skipped_count"] == 0

    def test_different_date_not_skipped(self, client, user, catalog):
        hgb = LabTestType.objects.get(abbreviation="hgb")
        LabResult.objects.create(
            user=user, test_type=hgb, value=12.5, unit="g/dL",
            source_text="12.5", source_unit="g/dL", source="manual",
            measured_at=date(2026, 2, 15),  # different date
        )

        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                ]
            },
            format="json",
        )
        assert response.json()["saved_count"] == 1

    def test_undated_row_never_dedups(self, client, user, catalog):
        """A row with no measured_at can't be compared — we err on the side of
        saving and letting the patient dedup later."""
        hgb = LabTestType.objects.get(abbreviation="hgb")
        LabResult.objects.create(
            user=user, test_type=hgb, value=12.5, unit="g/dL",
            source_text="12.5", source_unit="g/dL", source="manual",
            measured_at=None,
        )

        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL"},  # no measured_at
                ]
            },
            format="json",
        )
        assert response.json()["saved_count"] == 1


# ── Error paths ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCommitErrors:
    def test_not_completed_upload_returns_400(self, client, user, catalog):
        upload = LabUpload.objects.create(
            user=user, status=LabUploadStatus.PENDING,
        )
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={"accepted": []},
            format="json",
        )
        assert response.status_code == 400
        assert "ready to commit" in str(response.content).lower()

    def test_other_users_upload_returns_404(self, client, other_client, user, catalog):
        upload = _make_completed_upload(user, catalog)
        response = other_client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={"accepted": []},
            format="json",
        )
        assert response.status_code == 404

    def test_invalid_source_index_rejected(self, client, user, catalog):
        upload = _make_completed_upload(user, catalog)
        hgb = LabTestType.objects.get(abbreviation="hgb")
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 99, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL"},
                ]
            },
            format="json",
        )
        assert response.status_code == 400
        assert "source_index" in str(response.content).lower()

    def test_unknown_test_type_id_rejected(self, client, user, catalog):
        upload = _make_completed_upload(user, catalog)
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": 99999, "value": 12.5,
                     "unit": "g/dL"},
                ]
            },
            format="json",
        )
        assert response.status_code == 400

    def test_transaction_rolls_back_on_any_failure(self, client, user, catalog):
        """If any accepted row fails validation, NOTHING gets saved — even
        rows earlier in the list."""
        upload = _make_completed_upload(user, catalog)
        hgb = LabTestType.objects.get(abbreviation="hgb")
        response = client.post(
            reverse("lab-upload-commit", args=[upload.id]),
            data={
                "accepted": [
                    {"source_index": 0, "test_type_id": hgb.id, "value": 12.5,
                     "unit": "g/dL", "measured_at": "2026-03-15"},
                    # Invalid — unknown test_type_id
                    {"source_index": 1, "test_type_id": 99999, "value": 7.2,
                     "unit": "10^3/uL"},
                ]
            },
            format="json",
        )
        assert response.status_code == 400
        assert LabResult.objects.count() == 0  # nothing saved


# ── Retry extraction endpoint ───────────────────────────────────────────────

@pytest.mark.django_db
class TestExtractRetry:
    def test_resets_and_re_enqueues(self, client, user, catalog, settings):
        """A failed upload can be retried via POST /extract/. The response
        returns the upload with the fresh task wiring."""
        settings.ANTHROPIC_API_KEY = "sk-fake"
        upload = LabUpload.objects.create(
            user=user,
            status=LabUploadStatus.FAILED,
            error_message="Previous failure",
            parsed_results=[{"old": "data"}],
        )

        with patch("apps.labs.tasks._run_extraction_pipeline", return_value=[]):
            response = client.post(
                reverse("lab-upload-extract", args=[upload.id]),
                format="json",
            )

        assert response.status_code == 202, response.content
        body = response.json()
        # Eager task ran and marked completed
        assert body["status"] == "completed"
        assert body["error_message"] == ""
        assert body["parsed_results"] == []

    def test_other_users_upload_returns_404(self, client, other_client, user, catalog):
        upload = LabUpload.objects.create(
            user=user, status=LabUploadStatus.FAILED,
        )
        response = other_client.post(
            reverse("lab-upload-extract", args=[upload.id]),
            format="json",
        )
        assert response.status_code == 404
