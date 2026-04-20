from django.contrib import admin

from .models import LabCategory, LabResult, LabTestType


@admin.register(LabCategory)
class LabCategoryAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "display_order")
    ordering = ("display_order",)


@admin.register(LabTestType)
class LabTestTypeAdmin(admin.ModelAdmin):
    list_display = ("abbreviation", "name", "category", "default_unit", "loinc_code")
    list_filter = ("category", "value_type")
    search_fields = ("abbreviation", "name", "loinc_code", "name_normalized")
    readonly_fields = ("name_normalized", "reference_ranges")


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ("user", "test_type", "value", "unit", "status", "measured_at", "source")
    list_filter = ("source", "status", "match_method", "reference_source")
    search_fields = ("user__email", "test_type__abbreviation", "test_type__name")
    readonly_fields = ("source_text", "source_unit", "created_at")
    raw_id_fields = ("user", "test_type")
