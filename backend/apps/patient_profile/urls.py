from django.urls import path

from .views import FormSettingsView, PatientInfoUserView, ProfileCompletenessView

urlpatterns = [
    path("patient-info/user/", PatientInfoUserView.as_view(), name="patient-info-user"),
    path("patient-info/profile-completeness/", ProfileCompletenessView.as_view(), name="profile-completeness"),
    path("form-settings/", FormSettingsView.as_view(), name="form-settings"),
]
