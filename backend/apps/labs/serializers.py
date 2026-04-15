"""
DRF serializers for the labs app.

Phase 2a endpoints:
  GET  /api/v1/labs/catalog/             → CatalogSerializer
  GET  /api/v1/labs/results/             → LabResultSerializer (list)
  POST /api/v1/labs/results/             → LabResultCreateSerializer
  GET  /api/v1/labs/results/{id}/        → LabResultSerializer
  DELETE /api/v1/labs/results/{id}/      → (no body)
"""
from rest_framework import serializers

from .models import (
    LabCategory,
    LabResult,
    LabTestType,
    MatchMethod,
    ReferenceSource,
    ValueType,
)
from .unit_converter import is_convertible, normalise  # noqa: F401


# ── Catalog ───────────────────────────────────────────────────────────────────

class LabCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabCategory
        fields = ("key", "name", "display_order")


class LabTestTypeSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="key", read_only=True)
    reference_ranges_by_unit = serializers.SerializerMethodField()

    class Meta:
        model = LabTestType
        fields = (
            "id",
            "abbreviation",
            "name",
            "loinc_code",
            "default_unit",
            "alternative_units",
            "sample_values",
            "aliases",
            "reference_ranges",
            "reference_ranges_by_unit",
            "value_type",
            "molecular_weight",
            "category",
            "display_order",
        )

    def get_reference_ranges_by_unit(self, obj: LabTestType) -> dict[str, list[float]]:
        """Pre-compute the reference range in every unit the UI may render.

        Keys: default_unit + each alternative_unit.
        Values: [min, max] as floats, converted via unit_converter (same code
        path used on LabResult save, so the numbers match).

        Returns {} when the test has no default range (e.g. qualitative
        infection screens, or M-spike where "default": [0, 0] collapses to
        nothing meaningful). UI treats an empty dict as "no range to show".
        """
        raw = obj.reference_ranges.get("default") if isinstance(obj.reference_ranges, dict) else None
        if not (isinstance(raw, list) and len(raw) == 2):
            return {}
        lo, hi = raw[0], raw[1]

        result: dict[str, list[float]] = {obj.default_unit: [float(lo), float(hi)]}
        for alt_unit in (obj.alternative_units or []):
            lo_alt = normalise(lo, obj.default_unit, alt_unit, obj.molecular_weight)
            hi_alt = normalise(hi, obj.default_unit, alt_unit, obj.molecular_weight)
            if lo_alt is None or hi_alt is None:
                # Graceful skip: if the converter can't translate this range
                # into this alt unit (e.g. missing MW), the UI just shows
                # no range for that unit rather than misleading numbers.
                continue
            result[alt_unit] = [round(lo_alt, 3), round(hi_alt, 3)]
        return result


class CatalogSerializer(serializers.Serializer):
    """Aggregated catalog payload for GET /catalog/."""
    categories = LabCategorySerializer(many=True)
    tests = LabTestTypeSerializer(many=True)


# ── Lab results ───────────────────────────────────────────────────────────────

class LabResultSerializer(serializers.ModelSerializer):
    test = serializers.SerializerMethodField()

    class Meta:
        model = LabResult
        fields = (
            "id",
            "test",
            "value",
            "value_qualitative",
            "unit",
            "source_text",
            "source_unit",
            "reference_min",
            "reference_max",
            "reference_source",
            "match_method",
            "source",
            "confidence",
            "status",
            "measured_at",
            "created_at",
        )
        read_only_fields = fields

    def get_test(self, obj: LabResult) -> dict:
        t = obj.test_type
        return {
            "id": t.id,
            "abbreviation": t.abbreviation,
            "name": t.name,
            "category": t.category.key,
            "default_unit": t.default_unit,
            "value_type": t.value_type,
        }


# ── Shared validation + normalisation helpers (used by both create + update) ─

def _validate_value_fields(attrs: dict, test_type: LabTestType) -> None:
    """Enforce the value/qualitative/unit rules for a single lab result
    payload. Raises ValidationError on failure. Called by both the create
    and update serializers so the rules stay in one place (DRY)."""
    is_qualitative = test_type.value_type == ValueType.QUALITATIVE
    has_value = attrs.get("value") is not None
    has_qualitative = bool(attrs.get("value_qualitative"))

    if is_qualitative and not has_qualitative:
        raise serializers.ValidationError(
            {"value_qualitative": "Qualitative tests require a value_qualitative."}
        )
    if not is_qualitative and not has_value:
        raise serializers.ValidationError({"value": "Numeric tests require a value."})

    if not is_qualitative:
        source_unit = attrs.get("unit") or test_type.default_unit
        if not is_convertible(source_unit, test_type.default_unit, test_type.molecular_weight):
            raise serializers.ValidationError(
                {
                    "unit": (
                        f"Cannot convert {source_unit!r} to {test_type.default_unit!r}. "
                        "Use the test's default unit or a compatible one."
                    )
                }
            )


def _apply_normalised_fields(
    validated_data: dict,
    test_type: LabTestType,
    result: LabResult,
) -> None:
    """Populate value/unit/reference/date fields on `result` from validated
    input, applying unit normalisation and reference-range precedence
    (report wins, catalog fallback — §CQ2).

    Does NOT touch provenance fields (source, match_method, confidence) —
    those are set on create and left alone on update so a manually-edited
    FHIR-sourced result keeps its origin trail, with just the value changed.
    """
    is_qualitative = test_type.value_type == ValueType.QUALITATIVE
    source_value = validated_data.get("value")
    source_unit = (validated_data.get("unit") or test_type.default_unit).strip()

    if is_qualitative:
        result.value = None
        result.value_qualitative = validated_data.get("value_qualitative", "").strip()
        result.source_text = result.value_qualitative
    else:
        value = normalise(
            source_value,
            source_unit,
            test_type.default_unit,
            molecular_weight=test_type.molecular_weight,
        )
        if value is None:
            raise serializers.ValidationError(
                {"value": "Unit conversion failed. Contact support if this persists."}
            )
        result.value = value
        result.value_qualitative = ""
        result.source_text = str(source_value)

    result.source_unit = source_unit
    result.unit = test_type.default_unit

    # Reference range — report wins when provided, else catalog default
    report_min = validated_data.get("reference_min")
    report_max = validated_data.get("reference_max")
    if report_min is not None and report_max is not None:
        result.reference_min = normalise(
            report_min, source_unit, test_type.default_unit, test_type.molecular_weight
        )
        result.reference_max = normalise(
            report_max, source_unit, test_type.default_unit, test_type.molecular_weight
        )
        result.reference_source = ReferenceSource.REPORT
    else:
        catalog_min, catalog_max = test_type.default_range()
        result.reference_min = catalog_min
        result.reference_max = catalog_max
        result.reference_source = (
            ReferenceSource.CATALOG if catalog_min is not None else ReferenceSource.NONE
        )

    result.measured_at = validated_data.get("measured_at")


class LabResultCreateSerializer(serializers.Serializer):
    """
    Manual entry payload for POST /labs/results/. Accepts raw values + units
    and does the normalisation server-side. The input unit can be anything
    the catalog test supports (convertible to default_unit); if not, 400.

    Fields:
        test_type_id    : int (required) — catalog row to file the result under
        value           : float | null — for numeric tests
        value_qualitative : str | null — for qualitative tests
        unit            : str (optional) — defaults to the test's default_unit
        measured_at     : date (optional)
        reference_min   : float | null — optional, report-sourced
        reference_max   : float | null — optional, report-sourced
    """

    test_type_id = serializers.IntegerField()
    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            test_type = LabTestType.objects.select_related("category").get(pk=attrs["test_type_id"])
        except LabTestType.DoesNotExist:
            raise serializers.ValidationError({"test_type_id": "Unknown test type."})
        _validate_value_fields(attrs, test_type)
        attrs["_test_type"] = test_type
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        test_type: LabTestType = validated_data["_test_type"]
        result = LabResult(
            user=request.user,
            test_type=test_type,
            match_method=MatchMethod.MANUAL,
            source="manual",
            confidence=1.0,
        )
        _apply_normalised_fields(validated_data, test_type, result)
        result.save()
        return result


class LabResultUpdateSerializer(serializers.Serializer):
    """
    Payload for PATCH /labs/results/{id}/. Accepts the same value/unit/date
    fields as create, EXCEPT test_type_id which is immutable — you can't
    turn a hemoglobin row into a creatinine row by editing it. Create a
    new row and delete the old one if that's what the user wants.

    Provenance fields (source, match_method, confidence) are NOT touched
    on update. A manually-edited document-extracted row keeps source=
    "document_extraction" but gets a fresh value. When upload lands in
    Phase 2b, we can decide whether an edit should bump confidence to 1.0
    (user has verified the value) — for now, leave it alone.
    """

    value = serializers.FloatField(required=False, allow_null=True)
    value_qualitative = serializers.CharField(required=False, allow_blank=True, max_length=32)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=32)
    measured_at = serializers.DateField(required=False, allow_null=True)
    reference_min = serializers.FloatField(required=False, allow_null=True)
    reference_max = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        if not self.instance:
            raise serializers.ValidationError("Update serializer requires an instance.")
        _validate_value_fields(attrs, self.instance.test_type)
        return attrs

    def update(self, instance, validated_data):
        _apply_normalised_fields(validated_data, instance.test_type, instance)
        instance.save()
        return instance
