"""DRF authentication backend that delegates to pluggable token providers.

Iterates over PARTNER_AUTH_PROVIDERS in order.  Each provider first gets
a lightweight ``can_handle()`` check (unverified JWT payload inspection —
no secrets, no external calls) before the real ``verify()`` is invoked.
This ensures tokens are never leaked to providers that shouldn't see them.
"""
from __future__ import annotations

import logging

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
            return None

        token = header[7:]
        providers = get_providers()
        if not providers:
            return None

        unverified = decode_jwt_unverified(token)

        for provider in providers:
            if not provider.can_handle(token, unverified):
                continue

            claims = provider.verify(token)
            if claims is None:
                continue

            field, value = provider.user_lookup(claims)
            user = self._get_or_create(provider, claims, field, value)
            return (user, claims.raw)

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
            return User.objects.get(**{field: value})
