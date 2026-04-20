"""
API tests for Phase 2a endpoints.

Covers catalog, manual entry (numeric + qualitative), filters, deletion,
and ownership/404 isolation.
"""
from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.labs.models import LabCategory, LabResult, LabTestType


@pytest.fixture
def catalog(db):
    """Load the real catalog fixture for every test that needs it."""
    call_command("loaddata", "lab_catalog.json", app_label="labs", verbosity=0)
    return {
        "hgb": LabTestType.objects.get(abbreviation="hgb"),
        "creatinine": LabTestType.objects.get(abbreviation="creatinine"),
        "calcium": LabTestType.objects.get(abbreviation="calcium"),
        "hiv_ab": LabTestType.objects.get(abbreviation="hiv_ab"),
    }


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


# ── Catalog ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCatalogEndpoint:
    def test_list_returns_categories_and_tests(self, client, catalog):
        response = client.get(reverse("lab-catalog"))
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "tests" in data
        assert len(data["categories"]) >= 7
        assert len(data["tests"]) >= 35

    def test_test_includes_loinc_and_metadata(self, client, catalog):
        response = client.get(reverse("lab-catalog"))
        hgb = next(t for t in response.json()["tests"] if t["abbreviation"] == "hgb")
        assert hgb["loinc_code"] == "718-7"
        assert hgb["default_unit"] == "g/dL"
        assert hgb["category"] == "cbc"

    def test_sample_values_present_for_every_unit(self, client, catalog):
        """Fixture invariant: every numeric test must have a sample_values
        entry for its default_unit AND every alternative_unit. Without this,
        the manual entry dialog falls back to a generic placeholder, which is
        a silent UX regression we don't want."""
        response = client.get(reverse("lab-catalog"))
        missing: list[str] = []
        for t in response.json()["tests"]:
            if t["value_type"] == "qualitative":
                continue
            required = [t["default_unit"], *t["alternative_units"]]
            for u in required:
                if u not in t["sample_values"]:
                    missing.append(f"{t['abbreviation']}[{u!r}]")
        assert not missing, f"missing sample_values: {missing}"

    def test_hgb_sample_values_shape(self, client, catalog):
        response = client.get(reverse("lab-catalog"))
        hgb = next(t for t in response.json()["tests"] if t["abbreviation"] == "hgb")
        assert hgb["sample_values"] == {"g/dL": "14.0", "g/L": "140"}

    def test_reference_ranges_by_unit_converts_to_alternative_units(self, client, catalog):
        """Hemoglobin range [12.0, 17.5] g/dL should convert to [120, 175] g/L."""
        response = client.get(reverse("lab-catalog"))
        hgb = next(t for t in response.json()["tests"] if t["abbreviation"] == "hgb")
        ranges = hgb["reference_ranges_by_unit"]
        assert ranges["g/dL"] == [12.0, 17.5]
        assert ranges["g/L"][0] == pytest.approx(120.0, rel=1e-6)
        assert ranges["g/L"][1] == pytest.approx(175.0, rel=1e-6)

    def test_reference_ranges_by_unit_molar_creatinine(self, client, catalog):
        """Creatinine range [0.6, 1.3] mg/dL should land near [53, 115] µmol/L."""
        response = client.get(reverse("lab-catalog"))
        cr = next(t for t in response.json()["tests"] if t["abbreviation"] == "creatinine")
        ranges = cr["reference_ranges_by_unit"]
        assert ranges["mg/dL"] == [0.6, 1.3]
        # 0.6 mg/dL ≈ 53.0 µmol/L, 1.3 mg/dL ≈ 114.9 µmol/L
        assert ranges["umol/L"][0] == pytest.approx(53.0, rel=1e-2)
        assert ranges["umol/L"][1] == pytest.approx(114.9, rel=1e-2)

    def test_reference_ranges_by_unit_covers_every_numeric_alt(self, client, catalog):
        """Invariant: every numeric test with a default range must surface
        converted ranges for default_unit AND every alternative_unit."""
        response = client.get(reverse("lab-catalog"))
        missing: list[str] = []
        for t in response.json()["tests"]:
            if t["value_type"] == "qualitative":
                continue
            # Skip tests with a collapsed "no-range" default like M-spike [0,0]
            default = t.get("reference_ranges", {}).get("default")
            if not (isinstance(default, list) and len(default) == 2):
                continue
            by_unit = t["reference_ranges_by_unit"]
            required = [t["default_unit"], *t["alternative_units"]]
            for u in required:
                if u not in by_unit:
                    missing.append(f"{t['abbreviation']}[{u!r}]")
        assert not missing, f"reference_ranges_by_unit missing: {missing}"

    def test_qualitative_test_has_empty_ranges_by_unit(self, client, catalog):
        response = client.get(reverse("lab-catalog"))
        hiv = next(t for t in response.json()["tests"] if t["abbreviation"] == "hiv_ab")
        assert hiv["reference_ranges_by_unit"] == {}

    def test_requires_authentication(self, catalog):
        client = APIClient()  # no auth
        response = client.get(reverse("lab-catalog"))
        assert response.status_code == 401


# ── Manual entry — numeric ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreateNumericResult:
    def test_happy_path_default_unit(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {
                "test_type_id": catalog["hgb"].id,
                "value": 12.5,
                "measured_at": "2026-03-15",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["value"] == 12.5
        assert body["unit"] == "g/dL"
        assert body["source"] == "manual"
        assert body["match_method"] == "manual"
        assert body["confidence"] == 1.0
        assert body["status"] in ("in_range", "above", "below")  # 12.5 is in range
        assert body["status"] == "in_range"
        assert body["reference_min"] == 12.0
        assert body["reference_max"] == 17.5
        assert body["reference_source"] == "catalog"

    def test_unit_conversion_applied(self, client, catalog):
        # Submit creatinine in µmol/L, expect storage in mg/dL
        response = client.post(
            reverse("lab-result-list"),
            {
                "test_type_id": catalog["creatinine"].id,
                "value": 88.4,
                "unit": "umol/L",
                "measured_at": "2026-03-15",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        body = response.json()
        # 88.4 µmol/L ≈ 1.0 mg/dL
        assert body["value"] == pytest.approx(1.0, rel=1e-2)
        assert body["unit"] == "mg/dL"
        assert body["source_text"] == "88.4"
        assert body["source_unit"] == "umol/L"

    def test_report_reference_range_wins(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {
                "test_type_id": catalog["hgb"].id,
                "value": 13.0,
                "measured_at": "2026-03-15",
                "reference_min": 11.5,
                "reference_max": 16.0,
            },
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["reference_min"] == 11.5
        assert body["reference_max"] == 16.0
        assert body["reference_source"] == "report"

    def test_out_of_range_below(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {"test_type_id": catalog["hgb"].id, "value": 9.0, "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "below"

    def test_out_of_range_above(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {"test_type_id": catalog["hgb"].id, "value": 20.0, "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "above"

    def test_missing_value_rejected(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {"test_type_id": catalog["hgb"].id, "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 400

    def test_unknown_test_type_rejected(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {"test_type_id": 99999, "value": 12.5, "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 400

    def test_incompatible_unit_rejected(self, client, catalog):
        # Trying to submit hemoglobin in some nonsense unit
        response = client.post(
            reverse("lab-result-list"),
            {
                "test_type_id": catalog["hgb"].id,
                "value": 1.0,
                "unit": "parsecs",
                "measured_at": "2026-03-15",
            },
            format="json",
        )
        assert response.status_code == 400


# ── Manual entry — qualitative ────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreateQualitativeResult:
    def test_hiv_reactive(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {
                "test_type_id": catalog["hiv_ab"].id,
                "value_qualitative": "non-reactive",
                "measured_at": "2026-03-15",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        body = response.json()
        assert body["value"] is None
        assert body["value_qualitative"] == "non-reactive"

    def test_qualitative_missing_rejected(self, client, catalog):
        response = client.post(
            reverse("lab-result-list"),
            {"test_type_id": catalog["hiv_ab"].id, "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 400


# ── List / filter / delete ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestListFilterDelete:
    def test_list_own_results_only(self, client, user, other_user, catalog):
        # One result for each user
        LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            reference_min=12.0, reference_max=17.5,
            measured_at=date(2026, 3, 15),
        )
        LabResult.objects.create(
            user=other_user, test_type=catalog["hgb"],
            value=14.0, unit="g/dL", source_text="14.0", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.get(reverse("lab-result-list"))
        assert response.status_code == 200
        data = response.json()["results"] if "results" in response.json() else response.json()
        # Paginated response uses "results" key
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        assert len(data) == 1
        assert data[0]["value"] == 12.5

    def test_filter_by_test_abbreviation(self, client, user, catalog):
        LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        LabResult.objects.create(
            user=user, test_type=catalog["creatinine"],
            value=1.0, unit="mg/dL", source_text="1.0", source_unit="mg/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.get(reverse("lab-result-list") + "?test=hgb")
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict) and "results" in data:
            data = data["results"]
        assert len(data) == 1
        assert data[0]["test"]["abbreviation"] == "hgb"

    def test_delete_own_result(self, client, user, catalog):
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.delete(reverse("lab-result-detail", args=[r.id]))
        assert response.status_code == 204
        assert not LabResult.objects.filter(pk=r.id).exists()

    def test_delete_other_users_result_404(self, client, other_user, catalog):
        r = LabResult.objects.create(
            user=other_user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.delete(reverse("lab-result-detail", args=[r.id]))
        assert response.status_code == 404
        assert LabResult.objects.filter(pk=r.id).exists()  # Untouched


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpdateResult:
    def test_patch_value(self, client, user, catalog):
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            reference_min=12.0, reference_max=17.5,
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {"value": 13.2, "unit": "g/dL", "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["value"] == pytest.approx(13.2)
        assert body["status"] == "in_range"
        assert body["source_text"] == "13.2"
        # DB reflects the new value
        r.refresh_from_db()
        assert r.value == pytest.approx(13.2)

    def test_patch_unit_triggers_renormalization(self, client, user, catalog):
        """Editing the unit converts the new value back to default_unit."""
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        # Submit 125 g/L — should be stored as 12.5 g/dL
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {"value": 125, "unit": "g/L", "measured_at": "2026-03-15"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["value"] == pytest.approx(12.5, rel=1e-6)
        assert body["unit"] == "g/dL"
        assert body["source_text"] == "125.0"
        assert body["source_unit"] == "g/L"

    def test_patch_measured_at_only(self, client, user, catalog):
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {"value": 12.5, "unit": "g/dL", "measured_at": "2026-02-01"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["measured_at"] == "2026-02-01"

    def test_patch_report_range_wins_over_catalog(self, client, user, catalog):
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            reference_min=12.0, reference_max=17.5,
            reference_source="catalog",
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {
                "value": 12.5, "unit": "g/dL", "measured_at": "2026-03-15",
                "reference_min": 11.0, "reference_max": 16.5,
            },
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["reference_min"] == 11.0
        assert body["reference_max"] == 16.5
        assert body["reference_source"] == "report"

    def test_patch_other_users_result_404(self, client, other_user, catalog):
        r = LabResult.objects.create(
            user=other_user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {"value": 99.0, "unit": "g/dL"},
            format="json",
        )
        assert response.status_code == 404
        r.refresh_from_db()
        assert r.value == 12.5  # untouched

    def test_patch_rejects_incompatible_unit(self, client, user, catalog):
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {"value": 1.0, "unit": "parsecs"},
            format="json",
        )
        assert response.status_code == 400
        r.refresh_from_db()
        assert r.value == 12.5  # untouched

    def test_patch_test_type_id_is_ignored(self, client, user, catalog):
        """test_type_id in the payload is silently dropped — the test row
        cannot be re-assigned to a different test."""
        r = LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        response = client.patch(
            reverse("lab-result-detail", args=[r.id]),
            {
                "test_type_id": catalog["creatinine"].id,  # attempt to hijack
                "value": 13.0, "unit": "g/dL",
            },
            format="json",
        )
        assert response.status_code == 200
        r.refresh_from_db()
        assert r.test_type_id == catalog["hgb"].id  # still hemoglobin


# ── Cascade delete — user deletion propagates (§9.5) ──────────────────────────

@pytest.mark.django_db
class TestUserDeletionCascade:
    def test_deleting_user_wipes_lab_results(self, user, catalog):
        LabResult.objects.create(
            user=user, test_type=catalog["hgb"],
            value=12.5, unit="g/dL", source_text="12.5", source_unit="g/dL",
            measured_at=date(2026, 3, 15),
        )
        LabResult.objects.create(
            user=user, test_type=catalog["creatinine"],
            value=1.0, unit="mg/dL", source_text="1.0", source_unit="mg/dL",
            measured_at=date(2026, 3, 15),
        )
        assert LabResult.objects.filter(user=user).count() == 2

        user.delete()

        assert LabResult.objects.count() == 0
