"""Tests for phr acting as the identity provider for sibling services:
JWKS publishing, token introspection, logout blacklisting, shared claims."""
import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.tokens import jwks_document, tokens_for_user


@pytest.fixture
def user(db, user_factory):
    return user_factory(email="dana@example.com")


@pytest.mark.django_db
def test_tokens_carry_shared_claims(user):
    tokens = tokens_for_user(user)
    access = AccessToken(tokens["access"])
    assert access["email"] == "dana@example.com"
    assert access["identity_level"] == "ial1"
    assert access["claims"] == {"ADMIN": False, "MEDICAL_RECORDS": False}


@pytest.mark.django_db
def test_login_token_carries_shared_claims(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "dana@example.com", "password": "testpass123"},
        format="json",
    )
    assert response.status_code == 200
    access = AccessToken(response.json()["access"])
    assert access["email"] == "dana@example.com"


def test_jwks_empty_without_rsa_key(api_client, db):
    # Dev default is HS256 — the JWKS document must be an empty key set.
    response = api_client.get("/api/v1/auth/jwks/")
    assert response.status_code == 200
    assert response.json() == {"keys": []}


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
def test_introspect_valid_token(api_client, user):
    tokens = tokens_for_user(user)
    response = api_client.post(
        "/api/v1/auth/introspect/", {"token": tokens["access"]}, format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["email"] == "dana@example.com"
    assert data["user_id"] == user.id
    assert data["claims"] == {"ADMIN": False, "MEDICAL_RECORDS": False}


@pytest.mark.django_db
def test_introspect_garbage_token(api_client):
    response = api_client.post(
        "/api/v1/auth/introspect/", {"token": "not-a-jwt"}, format="json"
    )
    assert response.status_code == 200
    assert response.json() == {"active": False}


@pytest.mark.django_db
def test_introspect_inactive_user(api_client, user):
    tokens = tokens_for_user(user)
    user.is_active = False
    user.save()
    response = api_client.post(
        "/api/v1/auth/introspect/", {"token": tokens["access"]}, format="json"
    )
    assert response.json() == {"active": False}


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(authed_client):
    client, user = authed_client
    tokens = tokens_for_user(user)
    response = client.post(
        "/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
    )
    assert response.status_code == 204

    # The blacklisted refresh token must no longer refresh.
    client.credentials()
    refresh_response = client.post(
        "/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
    )
    assert refresh_response.status_code == 401
