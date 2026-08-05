from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminViewSet,
    EmailTokenObtainPairView,
    IntrospectView,
    JWKSView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    # Service-to-service verification against phr accounts
    path("jwks/", JWKSView.as_view(), name="auth-jwks"),
    path("introspect/", IntrospectView.as_view(), name="auth-introspect"),
    # Admin role management
    path("admins/", AdminViewSet.as_view({"get": "list_admins"}), name="auth-admins"),
    path("set-claims/", AdminViewSet.as_view({"post": "set_claims"}), name="auth-set-claims"),
]
