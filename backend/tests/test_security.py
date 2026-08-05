import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestEmailUniqueness:
    def test_unique_constraint_enforced(self, user_factory):
        user_factory(email="same@test.com")
        with pytest.raises(IntegrityError):
            user_factory(email="same@test.com")


@pytest.mark.django_db
class TestNoEmailEnumeration:
    def test_check_email_endpoint_absent(self, api_client):
        resp = api_client.post(
            "/api/v1/auth/check-email/",
            {"email": "test@example.com"},
            format="json",
        )
        assert resp.status_code == 404


class TestThrottling:
    def test_anon_rate_limit(self):
        from unittest.mock import MagicMock

        from django.core.cache import cache
        from rest_framework.throttling import AnonRateThrottle

        cache.clear()

        class TestThrottle(AnonRateThrottle):
            rate = "30/minute"
            THROTTLE_RATES = {"anon": "30/minute"}

        throttle = TestThrottle()

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.1"}
        request.user.is_authenticated = False

        for i in range(30):
            assert throttle.allow_request(request, None), f"Request {i+1} should pass"

        assert not throttle.allow_request(request, None), "Request 31 should be throttled"
