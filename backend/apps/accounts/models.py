from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Email-first user — the canonical account record for the whole
    HealthKey service family. Sibling services verify phr-issued JWTs
    instead of holding their own credentials."""

    IDENTITY_LEVELS = [
        ("ial1", "IAL1 — Email verified"),
        ("ial2", "IAL2 — Identity proofed"),
    ]

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    identity_level = models.CharField(
        max_length=4,
        choices=IDENTITY_LEVELS,
        default="ial1",
    )
    is_admin = models.BooleanField(
        default=False,
        help_text="ADMIN role — grants access to the admin panel",
    )
    has_medical_records = models.BooleanField(
        default=False,
        help_text="MEDICAL_RECORDS role — grants access to clinical record tooling",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]

    @property
    def claims(self) -> dict:
        return {
            "ADMIN": self.is_admin,
            "MEDICAL_RECORDS": self.has_medical_records,
        }

    def __str__(self):
        return self.email
