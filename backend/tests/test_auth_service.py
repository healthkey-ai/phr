"""Tests for phr acting as the identity provider for sibling services:
JWKS publishing, token introspection, logout blacklisting, shared claims."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.accounts.tokens import jwks_document, tokens_for_user


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="dana@example.com", password="Strong-Pass-123!")


@pytest.mark.django_db
def test_tokens_carry_shared_claims(user):
    tokens = tokens_for_user(user)
    access = AccessToken(tokens["access"])
    assert access["email"] == "dana@example.com"
    assert access["identity_level"] == "unverified"


@pytest.mark.django_db
def test_login_token_carries_shared_claims(client, user):
    response = client.post(
        reverse("auth-login"),
        {"email": "dana@example.com", "password": "Strong-Pass-123!"},
        format="json",
    )
    assert response.status_code == 200
    access = AccessToken(response.data["access"])
    assert access["email"] == "dana@example.com"


def test_jwks_empty_without_rsa_key(client, db):
    # Dev default is HS256 — the JWKS document must be an empty key set.
    response = client.get(reverse("auth-jwks"))
    assert response.status_code == 200
    assert response.data == {"keys": []}


def test_jwks_document_with_rsa_key(settings):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings.JWT_PUBLIC_KEY = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    doc = jwks_document()
    assert len(doc["keys"]) == 1
    jwk = doc["keys"][0]
    assert jwk["kty"] == "RSA"
    assert jwk["alg"] == "RS256"
    assert jwk["kid"] and jwk["n"] and jwk["e"]


@pytest.mark.django_db
def test_introspect_valid_token(client, user):
    tokens = tokens_for_user(user)
    response = client.post(
        reverse("auth-introspect"), {"token": tokens["access"]}, format="json"
    )
    assert response.status_code == 200
    assert response.data["active"] is True
    assert response.data["email"] == "dana@example.com"
    assert response.data["user_id"] == user.id


@pytest.mark.django_db
def test_introspect_garbage_token(client):
    response = client.post(
        reverse("auth-introspect"), {"token": "not-a-jwt"}, format="json"
    )
    assert response.status_code == 200
    assert response.data == {"active": False}


@pytest.mark.django_db
def test_introspect_inactive_user(client, user):
    tokens = tokens_for_user(user)
    user.is_active = False
    user.save()
    response = client.post(
        reverse("auth-introspect"), {"token": tokens["access"]}, format="json"
    )
    assert response.data == {"active": False}


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(client, user):
    tokens = tokens_for_user(user)
    client.force_authenticate(user=user)
    response = client.post(
        reverse("auth-logout"), {"refresh": tokens["refresh"]}, format="json"
    )
    assert response.status_code == 204

    # The blacklisted refresh token must no longer refresh.
    client.force_authenticate(user=None)
    refresh_response = client.post(
        reverse("auth-refresh"), {"refresh": tokens["refresh"]}, format="json"
    )
    assert refresh_response.status_code == 401
