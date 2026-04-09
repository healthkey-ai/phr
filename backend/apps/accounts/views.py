from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .serializers import RegisterSerializer, UserSerializer


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
