from django.urls import path

from . import views

urlpatterns = [
    path("", views.PatientProfileView.as_view(), name="patient_profile"),
]
