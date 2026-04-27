from django.contrib import admin

from .models import LabTestEntry, LabValue, LoincAlias, LoincEntry


@admin.register(LoincEntry)
class LoincEntryAdmin(admin.ModelAdmin):
    list_display = ("code", "short_name", "category", "system", "default_unit", "status")
    list_filter = ("status", "category")
    search_fields = ("code", "short_name", "component")


@admin.register(LoincAlias)
class LoincAliasAdmin(admin.ModelAdmin):
    list_display = ("text", "loinc_entry", "source")
    list_filter = ("source",)
    search_fields = ("text", "text_normalized", "loinc_entry__code")
    raw_id_fields = ("loinc_entry",)


@admin.register(LabTestEntry)
class LabTestEntryAdmin(admin.ModelAdmin):
    list_display = ("abbreviation", "name", "category", "default_unit")
    list_filter = ("value_type",)
    search_fields = ("abbreviation", "name", "name_normalized")
    readonly_fields = ("name_normalized",)
    raw_id_fields = ("loinc_entry",)


@admin.register(LabValue)
class LabValueAdmin(admin.ModelAdmin):
    list_display = ("user", "test_entry", "value", "unit", "status", "measured_at", "source")
    list_filter = ("source", "status", "match_method", "reference_source")
    search_fields = ("user__email", "test_entry__abbreviation", "test_entry__name")
    readonly_fields = ("source_text", "source_unit", "created_at")
    raw_id_fields = ("user", "test_entry", "loinc_entry")
