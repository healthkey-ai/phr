from django.contrib import admin

from .models import PatientInfo, PatientInfoVersion


@admin.register(PatientInfo)
class PatientInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "disease", "completeness_score", "updated_at")
    search_fields = ("user__email", "first_name", "last_name")
    readonly_fields = ("bmi", "completeness_score", "completeness_by_category", "created_at", "updated_at")


@admin.register(PatientInfoVersion)
class PatientInfoVersionAdmin(admin.ModelAdmin):
    list_display = ("patient_info", "source", "changed_by", "timestamp")
    list_filter = ("source",)
    readonly_fields = ("patient_info", "changed_fields", "changed_by", "source", "timestamp")
