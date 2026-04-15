"""Smoke tests verifying the auth + patient profile flow end to end."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.patient_profile.models import PatientInfo


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_register_creates_user_and_patient_info(client):
    response = client.post(
        reverse("auth-register"),
        {"email": "alice@example.com", "password": "Strong-Pass-123!"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user"]["email"] == "alice@example.com"
    assert "access" in response.data["tokens"]
    assert "refresh" in response.data["tokens"]

    user = User.objects.get(email="alice@example.com")
    assert PatientInfo.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_login_returns_tokens(client):
    User.objects.create_user(email="bob@example.com", password="Strong-Pass-123!")
    response = client.post(
        reverse("auth-login"),
        {"email": "bob@example.com", "password": "Strong-Pass-123!"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_patient_info_get_and_patch(client):
    user = User.objects.create_user(email="carol@example.com", password="Strong-Pass-123!")
    PatientInfo.objects.create(user=user)
    client.force_authenticate(user=user)

    # GET
    r1 = client.get(reverse("patient-info-user"))
    assert r1.status_code == 200
    assert r1.data["first_name"] == ""

    # PATCH demographics
    r2 = client.patch(
        reverse("patient-info-user"),
        {
            "first_name": "Carol",
            "last_name": "Smith",
            "dob": "1968-04-14",
            "gender": "female",
            "height_cm": 168,
            "weight_kg": 65,
        },
        format="json",
    )
    assert r2.status_code == 200
    assert r2.data["first_name"] == "Carol"
    # BMI should be auto-calculated: 65 / (1.68 ** 2) ≈ 23.03
    assert r2.data["bmi"] is not None
    assert 22.5 < r2.data["bmi"] < 23.5

    # PATCH details — should merge, not replace
    r3 = client.patch(
        reverse("patient-info-user"),
        {"details": {"conditions": ["diabetes"], "smokingStatus": "never"}},
        format="json",
    )
    assert r3.status_code == 200
    assert "diabetes" in r3.data["details"]["conditions"]
    assert r3.data["details"]["smokingStatus"] == "never"

    r4 = client.patch(
        reverse("patient-info-user"),
        {"details": {"alcoholFrequency": "rarely"}},
        format="json",
    )
    # Original details preserved
    assert "conditions" in r4.data["details"]
    assert r4.data["details"]["alcoholFrequency"] == "rarely"


@pytest.mark.django_db
def test_completeness_endpoint(client):
    user = User.objects.create_user(email="dan@example.com", password="Strong-Pass-123!")
    client.force_authenticate(user=user)

    response = client.get(reverse("profile-completeness"))
    assert response.status_code == 200
    assert "completeness_score" in response.data
    assert "completeness_by_category" in response.data


@pytest.mark.django_db
def test_form_settings_endpoint(client):
    user = User.objects.create_user(email="eve@example.com", password="Strong-Pass-123!")
    client.force_authenticate(user=user)

    response = client.get(reverse("form-settings"))
    assert response.status_code == 200
    assert "gender" in response.data
    assert "diseases" in response.data
    assert "common_conditions" in response.data


@pytest.mark.django_db
def test_unauthenticated_access_blocked(client):
    response = client.get(reverse("patient-info-user"))
    assert response.status_code == 401
