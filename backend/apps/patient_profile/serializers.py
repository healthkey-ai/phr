import json

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers

from .models import PatientInfo


class PatientInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientInfo
        fields = (
            "id",
            "first_name",
            "last_name",
            "dob",
            "gender",
            "ethnicity",
            "height_cm",
            "weight_kg",
            "bmi",
            "country",
            "postal_code",
            "geo_lat",
            "geo_long",
            "languages",
            "insurance_status",
            "employment_status",
            "disease",
            "details",
            "completeness_score",
            "completeness_by_category",
            "updated_at",
        )
        read_only_fields = ("id", "bmi", "completeness_score", "completeness_by_category", "updated_at")

    def update(self, instance, validated_data):
        """
        Merge `details` JSONB on PATCH instead of replacing it.
        Replacement would lose unrelated fields when the client only sends a subset.
        """
        new_details = validated_data.pop("details", None)
        if new_details is not None:
            merged = dict(instance.details or {})
            merged.update(new_details)
            instance.details = merged

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Audit trail — record what changed.
        # Round-trip through DjangoJSONEncoder so dates/decimals serialize cleanly.
        changed_payload = {**validated_data}
        if new_details is not None:
            changed_payload["details"] = new_details
        changed_payload = json.loads(json.dumps(changed_payload, cls=DjangoJSONEncoder))

        from .models import PatientInfoVersion
        PatientInfoVersion.objects.create(
            patient_info=instance,
            changed_fields=changed_payload,
            changed_by=self.context["request"].user,
            source="manual",
        )
        return instance


class ProfileCompletenessSerializer(serializers.Serializer):
    completeness_score = serializers.FloatField()
    completeness_by_category = serializers.DictField()
