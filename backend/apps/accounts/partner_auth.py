"""DRF authentication backend that delegates to pluggable token providers.

Iterates over PARTNER_AUTH_PROVIDERS in order.  Each provider first gets
a lightweight ``can_handle()`` check (unverified JWT payload inspection —
no secrets, no external calls) before the real ``verify()`` is invoked.
This ensures tokens are never leaked to providers that shouldn't see them.
"""
from __future__ import annotations

import logging
import traceback

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.authentication import BaseAuthentication

from .providers import get_providers
from .providers.base import decode_jwt_unverified

logger = logging.getLogger(__name__)

User = get_user_model()


class PartnerAuthentication(BaseAuthentication):

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            logger.debug("partner_auth: no Bearer token")
            return None

        token = header[7:]
        providers = get_providers()
        if not providers:
            logger.warning("partner_auth: no providers configured")
            return None

        unverified = decode_jwt_unverified(token)
        logger.info(
            "partner_auth: iss=%s sub=%s email=%s",
            (unverified or {}).get("iss", "?"),
            (unverified or {}).get("sub", "?"),
            (unverified or {}).get("email", "?"),
        )

        for provider in providers:
            if not provider.can_handle(token, unverified):
                continue

            try:
                claims = provider.verify(token)
            except Exception as exc:
                logger.error(
                    "partner_auth: %s.verify raised %s: %s\n%s",
                    type(provider).__name__, type(exc).__name__, exc,
                    traceback.format_exc(),
                )
                raise

            if claims is None:
                logger.warning("partner_auth: %s.verify returned None", type(provider).__name__)
                continue

            field, value = provider.user_lookup(claims)
            try:
                user = self._get_or_create(provider, claims, field, value)
            except Exception as exc:
                logger.error(
                    "partner_auth: _get_or_create failed for %s=%s: %s\n%s",
                    field, value, exc, traceback.format_exc(),
                )
                raise

            logger.info("partner_auth: authenticated user=%s (id=%s) via %s", user, user.pk, type(provider).__name__)
            return (user, claims.raw)

        logger.warning("partner_auth: no provider handled the token")
        return None

    @staticmethod
    def _get_or_create(provider, claims, field, value):
        try:
            return User.objects.get(**{field: value})
        except User.DoesNotExist:
            pass

        defaults = provider.provision_defaults(claims)
        try:
            user = User.objects.create_user(
                email=defaults.pop("email", f"{value}@partner.local"),
                **defaults,
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            logger.info(
                "partner_auth: provisioned user %d via %s (%s=%s)",
                user.pk,
                type(provider).__name__,
                field,
                value,
            )
            return user
        except IntegrityError:
            email = claims.email or defaults.get("email", "")
            try:
                user = User.objects.get(**{field: value})
            except User.DoesNotExist:
                user = User.objects.get(email=email)
                setattr(user, field, value)
                user.save(update_fields=[field])
                logger.info(
                    "partner_auth: linked %s=%s to existing user %d (%s)",
                    field, value, user.pk, email,
                )
            return user
