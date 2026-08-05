from rest_framework import serializers

from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ("id", "onboarding_step", "details", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
