from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdmin
from .serializers import EmailTokenObtainPairSerializer, RegisterSerializer, UserSerializer
from .services import CLAIM_TO_FIELD, sync_claims_to_user
from .tokens import jwks_document, tokens_for_user

User = get_user_model()


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Body: { "email", "password", "first_name"?, "last_name"? }
    Response: { "user": {...}, "tokens": { "access", "refresh" } }
    """

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveAPIView):
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
                "user_id": user.id,
                "email": token.get("email", user.email),
                "identity_level": token.get("identity_level", user.identity_level),
                "claims": token.get("claims", user.claims),
                "exp": token["exp"],
                "iss": token.get("iss"),
            }
        )


class AdminViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = UserSerializer

    @action(detail=False, methods=["get"], url_path="admins")
    def list_admins(self, request):
        """List users holding at least one role, for the roles panel."""
        users = User.objects.order_by("email")
        return Response(self.get_serializer(users, many=True).data)

    @action(detail=False, methods=["post"], url_path="set-claims")
    def set_claims(self, request):
        """Set ADMIN / MEDICAL_RECORDS roles for a user (DB is the sole
        source of truth — no external identity provider to sync)."""
        user_id = request.data.get("user_id")
        new_claims = request.data.get("claims", {})

        if not user_id:
            return Response({"error": "user_id required"}, status=status.HTTP_400_BAD_REQUEST)

        if not set(new_claims.keys()).issubset(CLAIM_TO_FIELD):
            return Response(
                {"error": f"Only {set(CLAIM_TO_FIELD)} claims can be set"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        sync_claims_to_user(target, new_claims)
        target.save(update_fields=list(CLAIM_TO_FIELD.values()))

        return Response(self.get_serializer(target).data)
