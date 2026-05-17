import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .serializers import RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """SimpleJWT defaults to USERNAME_FIELD which we set to 'email' on the User model."""
    username_field = "email"


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

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
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


class PartnerTokenView(APIView):
    """Exchange a partner token for PHR JWT credentials.

    Accepts any token recognised by the configured PARTNER_AUTH_PROVIDERS
    (Firebase, external JWT, etc.) and returns a PHR access + refresh pair.
    Host apps that prefer explicit token exchange over direct bearer auth
    use this endpoint before mounting the federated labs module.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .providers import get_providers
        from .providers.base import decode_jwt_unverified
        from .partner_auth import PartnerAuthentication

        token = request.data.get("token", "") or request.data.get("firebase_token", "")
        if not token:
            return Response(
                {"detail": "token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        providers = get_providers()
        unverified = decode_jwt_unverified(token)
        user = None
        for provider in providers:
            if not provider.can_handle(token, unverified):
                continue
            claims = provider.verify(token)
            if claims is None:
                continue
            field, value = provider.user_lookup(claims)
            user = PartnerAuthentication._get_or_create(provider, claims, field, value)
            break

        if user is None:
            return Response(
                {"detail": "Token not recognised by any configured provider"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user.pk,
        })
