"""Token issuance and the JWKS document.

phr is the identity provider for the HealthKey service family. Every token
carries `email`, `identity_level`, and role claims so sibling services can
resolve the account without a callback to phr.
"""
import base64
import hashlib
import json

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def set_shared_claims(token, user):
    token["email"] = user.email
    token["identity_level"] = user.identity_level
    token["claims"] = user.claims


def tokens_for_user(user):
    """Issue an access/refresh pair with the shared cross-service claims."""
    refresh = RefreshToken.for_user(user)
    set_shared_claims(refresh, user)
    access = refresh.access_token
    set_shared_claims(access, user)
    return {"access": str(access), "refresh": str(refresh)}


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def jwks_document() -> dict:
    """RFC 7517 JWKS built from JWT_PUBLIC_KEY.

    Empty key set when running HS256 (local dev without an RSA keypair) —
    sibling services must use POST /api/v1/auth/introspect/ in that mode.
    """
    pem = settings.JWT_PUBLIC_KEY
    if not pem:
        return {"keys": []}

    from cryptography.hazmat.primitives import serialization

    public_key = serialization.load_pem_public_key(pem.encode())
    numbers = public_key.public_numbers()
    n = _b64url_uint(numbers.n)
    e = _b64url_uint(numbers.e)

    # RFC 7638 thumbprint as a stable kid
    thumbprint_input = json.dumps(
        {"e": e, "kty": "RSA", "n": n}, separators=(",", ":"), sort_keys=True
    ).encode()
    kid = (
        base64.urlsafe_b64encode(hashlib.sha256(thumbprint_input).digest())
        .rstrip(b"=")
        .decode("ascii")
    )

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": n,
                "e": e,
            }
        ]
    }
