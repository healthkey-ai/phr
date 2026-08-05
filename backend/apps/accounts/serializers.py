from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .tokens import set_shared_claims


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """SimpleJWT defaults to USERNAME_FIELD, which the User model sets to 'email'.

    Adds the shared cross-service claims so any phr-issued token is
    self-describing for sibling services.
    """

    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        set_shared_claims(token, user)
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("id", "email", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "identity_level", "mfa_enabled", "created_at")
        read_only_fields = fields
