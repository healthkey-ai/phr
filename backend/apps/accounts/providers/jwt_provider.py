from __future__ import annotations

import logging
from typing import Any

from .base import TokenClaims, TokenProvider

logger = logging.getLogger(__name__)


class LocalJWTProvider(TokenProvider):
    """Verify SimpleJWT access tokens issued by this PHR backend."""

    def can_handle(self, token: str, unverified_payload: dict[str, Any] | None) -> bool:
        if unverified_payload is None:
            return False
        return "user_id" in unverified_payload and "iss" not in unverified_payload

    def verify(self, token: str) -> TokenClaims | None:
        try:
            from rest_framework_simplejwt.tokens import AccessToken
        except ImportError:
            return None

        try:
            validated = AccessToken(token)
        except Exception:
            return None

        user_id = str(validated.get("user_id", ""))
        if not user_id:
            return None

        return TokenClaims(
            uid=user_id,
            email="",
            raw=dict(validated.payload),
        )

    def user_lookup(self, claims: TokenClaims) -> tuple[str, str]:
        return ("id", claims.uid)
