import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestRegister:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/register/"

    def test_creates_user_with_tokens(self):
        resp = self.client.post(
            self.url,
            {
                "email": "new@example.com",
                "password": "strong-pass-123",
                "first_name": "Jane",
                "last_name": "Doe",
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["first_name"] == "Jane"
        assert "access" in data["tokens"] and "refresh" in data["tokens"]
        assert User.objects.filter(email="new@example.com").exists()

    def test_duplicate_email(self):
        payload = {
            "email": "dup@example.com",
            "password": "strong-pass-123",
            "first_name": "A",
            "last_name": "B",
        }
        self.client.post(self.url, payload, format="json")
        resp = self.client.post(self.url, payload, format="json")
        assert resp.status_code == 400

    def test_short_password(self):
        resp = self.client.post(
            self.url,
            {
                "email": "short@example.com",
                "password": "abc",
                "first_name": "A",
                "last_name": "B",
            },
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMeEndpoint:
    def test_unauthenticated(self):
        client = APIClient()
        resp = client.get("/api/v1/auth/me/")
        assert resp.status_code in (401, 403)

    def test_returns_user_data(self, authed_client):
        client, user = authed_client
        resp = client.get("/api/v1/auth/me/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == user.email
        assert data["id"] == user.id
        assert "claims" in data


@pytest.mark.django_db
class TestAdminsEndpoint:
    def test_requires_admin(self, authed_client):
        client, _ = authed_client
        resp = client.get("/api/v1/auth/admins/")
        assert resp.status_code == 403

    def test_returns_users(self, admin_client, admin_user):
        resp = admin_client.get("/api/v1/auth/admins/")
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert admin_user.email in emails


@pytest.mark.django_db
class TestSetClaims:
    def test_requires_admin(self, authed_client):
        client, _ = authed_client
        resp = client.post(
            "/api/v1/auth/set-claims/",
            {"user_id": 1, "claims": {"ADMIN": True}},
            format="json",
        )
        assert resp.status_code == 403

    def test_rejects_unknown_claims(self, admin_client, user_factory):
        target = user_factory(email="target@example.com")
        resp = admin_client.post(
            "/api/v1/auth/set-claims/",
            {"user_id": target.id, "claims": {"SUPERPOWERS": True}},
            format="json",
        )
        assert resp.status_code == 400

    def test_updates_user(self, admin_client, user_factory):
        target = user_factory(email="staffer@example.com")
        assert not target.is_admin
        resp = admin_client.post(
            "/api/v1/auth/set-claims/",
            {"user_id": target.id, "claims": {"ADMIN": True}},
            format="json",
        )
        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_admin is True

    def test_can_demote(self, admin_client, user_factory):
        target = user_factory(email="demote@example.com", is_admin=True)
        resp = admin_client.post(
            "/api/v1/auth/set-claims/",
            {"user_id": target.id, "claims": {"ADMIN": False}},
            format="json",
        )
        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_admin is False
