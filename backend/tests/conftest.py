import factory
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "Test"
    last_name = "User"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "testpass123")
        user = model_class(**kwargs)
        user.set_password(password)
        user.save()
        return user


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def api_client():
    return APIClient()


def _login(api_client, user):
    token = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "testpass123"},
        format="json",
    ).json()["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authed_client(user_factory, api_client):
    user = user_factory()
    return _login(api_client, user), user


@pytest.fixture
def admin_user(user_factory):
    return user_factory(email="admin@example.com", is_admin=True)


@pytest.fixture
def admin_client(admin_user, api_client):
    return _login(api_client, admin_user)
