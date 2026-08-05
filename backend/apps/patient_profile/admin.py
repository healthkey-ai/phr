from django.contrib import admin

from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "onboarding_step", "updated_at")
    list_filter = ("onboarding_step",)
    search_fields = ("user__email",)
