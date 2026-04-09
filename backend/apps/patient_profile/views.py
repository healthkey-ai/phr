from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .form_settings import FORM_SETTINGS
from .models import PatientInfo
from .serializers import PatientInfoSerializer, ProfileCompletenessSerializer


class PatientInfoUserView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/patient-info/user/   — fetch current user's PatientInfo
    PATCH /api/v1/patient-info/user/   — update current user's PatientInfo
    """

    serializer_class = PatientInfoSerializer

    def get_object(self):
        obj, _ = PatientInfo.objects.get_or_create(user=self.request.user)
        return obj


class ProfileCompletenessView(APIView):
    """
    GET /api/v1/patient-info/profile-completeness/
    Returns the completeness score + per-category breakdown.
    """

    def get(self, request, *args, **kwargs):
        info, _ = PatientInfo.objects.get_or_create(user=request.user)
        info.recompute_completeness()
        info.save(update_fields=["completeness_score", "completeness_by_category"])
        serializer = ProfileCompletenessSerializer(info)
        return Response(serializer.data)


class FormSettingsView(APIView):
    """
    GET /api/v1/form-settings/
    Returns dropdown options for all select/multiselect fields.
    """

    def get(self, request, *args, **kwargs):
        return Response(FORM_SETTINGS)
