from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import EmailTokenObtainPairSerializer, RegisterSerializer, UserSerializer
from .tokens import jwks_document, tokens_for_user


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Body: { "email": "...", "password": "..." }
    Response: { "user": {...}, "tokens": { "access": "...", "refresh": "..." } }
    """

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Auto-create empty PatientInfo on registration
        from apps.patient_profile.models import PatientInfo
        PatientInfo.objects.get_or_create(user=user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens_for_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveAPIView):
    """
    GET /api/v1/auth/me/
    Returns the currently authenticated user.
    """

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Body: { "refresh": "..." }
    Blacklists the refresh token so it can't be used again.
    """

    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh", "")).blacklist()
        except TokenError:
            pass  # already expired/blacklisted — logout is idempotent
        return Response(status=status.HTTP_204_NO_CONTENT)


class JWKSView(APIView):
    """
    GET /api/v1/auth/jwks/
    Public keys for offline verification of phr-issued RS256 tokens.
    Sibling services fetch this once and verify tokens locally.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response(jwks_document())


class IntrospectView(APIView):
    """
    POST /api/v1/auth/introspect/
    Body: { "token": "<access token>" }
    RFC 7662-shaped response: { "active": bool, ...claims }.

    Fallback verification path for sibling services when phr runs HS256
    (no RSA keypair configured) or when they want revocation-aware checks.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            token = AccessToken(request.data.get("token", ""))
        except TokenError:
            return Response({"active": False})

        user = User.objects.filter(id=token.get("user_id"), is_active=True).first()
        if user is None:
            return Response({"active": False})

        return Response(
            {
                "active": True,
                "user_id": token["user_id"],
                "email": token.get("email", user.email),
                "identity_level": token.get("identity_level", user.identity_level),
                "exp": token["exp"],
                "iss": token.get("iss"),
            }
        )
