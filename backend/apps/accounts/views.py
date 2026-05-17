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
    """Exchange a Firebase ID token for PHR JWT credentials.

    Called by host apps before mounting the federated labs module.
    Verifies the Firebase token, finds or creates a linked PHR user,
    and returns a PHR access + refresh token pair.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        firebase_token = request.data.get("firebase_token", "")
        if not firebase_token:
            return Response(
                {"detail": "firebase_token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from firebase_admin import auth as firebase_auth

            decoded = firebase_auth.verify_id_token(firebase_token)
        except Exception:
            return Response(
                {"detail": "Invalid Firebase token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        uid = decoded["uid"]
        email = decoded.get("email", "")

        user, created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={"email": email},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            logger.info(
                "partner_token: provisioned new PHR user %d for firebase_uid=%s",
                user.pk,
                uid,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user.pk,
            "created": created,
        })
