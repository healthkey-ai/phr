from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .tokens import set_shared_claims

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """USERNAME_FIELD is 'email' on the User model. Adds the shared
    cross-service claims so any phr-issued token is self-describing."""

    username_field = "email"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        set_shared_claims(token, user)
        return token


class UserSerializer(serializers.ModelSerializer):
    claims = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "identity_level",
            "is_admin",
            "has_medical_records",
            "claims",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name")
        read_only_fields = ("id",)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
