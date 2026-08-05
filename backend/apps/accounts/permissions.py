from rest_framework.permissions import BasePermission


def _claim_permission(field: str):
    """Factory for permissions that check a User model boolean field."""
    class ClaimPermission(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and getattr(user, field, False))
    return ClaimPermission


IsAdmin = _claim_permission("is_admin")
IsAdmin.__doc__ = "Requires the ADMIN role (User.is_admin)."

HasMedicalRecords = _claim_permission("has_medical_records")
HasMedicalRecords.__doc__ = "Requires the MEDICAL_RECORDS role."
