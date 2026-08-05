from rest_framework import generics

from .models import PatientProfile
from .serializers import PatientProfileSerializer


class PatientProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = PatientProfileSerializer

    def get_object(self):
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        return profile
