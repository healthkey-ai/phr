from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTest(TestCase):
    def test_health_endpoint(self):
        client = APIClient()
        response = client.get("/api/v1/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok"})


class AuthFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login(self):
        reg = self.client.post(
            "/api/v1/auth/register/",
            {"email": "test@example.com", "password": "testpass123", "first_name": "Test", "last_name": "User"},
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED)

        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn("access", login.json())

    def test_me_requires_auth(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_me_returns_user(self):
        self.client.post(
            "/api/v1/auth/register/",
            {"email": "me@example.com", "password": "testpass123", "first_name": "Me", "last_name": "User"},
            format="json",
        )
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "me@example.com", "password": "testpass123"},
            format="json",
        )
        token = login.json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["email"], "me@example.com")
