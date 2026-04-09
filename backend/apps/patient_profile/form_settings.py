"""
Form dropdown options served via /api/v1/form-settings/.

Source: docs/patient-app-requirements.md §2.
This is configuration data, not user data. It changes via deploy, not via API.
"""

FORM_SETTINGS = {
    "gender": [
        {"value": "male", "label": "Male"},
        {"value": "female", "label": "Female"},
        {"value": "non_binary", "label": "Non-binary"},
        {"value": "prefer_not_to_say", "label": "Prefer not to say"},
    ],
    "ethnicity": [
        {"value": "white", "label": "White"},
        {"value": "black", "label": "Black or African American"},
        {"value": "hispanic", "label": "Hispanic or Latino"},
        {"value": "asian", "label": "Asian"},
        {"value": "native", "label": "American Indian or Alaska Native"},
        {"value": "pacific", "label": "Native Hawaiian or Pacific Islander"},
        {"value": "middle_eastern", "label": "Middle Eastern or North African"},
        {"value": "other", "label": "Other"},
    ],
    "diseases": [
        {"value": "", "label": "None"},
        {"value": "multiple_myeloma", "label": "Multiple Myeloma"},
        {"value": "breast", "label": "Breast Cancer"},
        {"value": "follicular_lymphoma", "label": "Follicular Lymphoma"},
        {"value": "cll", "label": "Chronic Lymphocytic Leukemia (CLL)"},
        {"value": "lung", "label": "Lung Cancer"},
        {"value": "prostate", "label": "Prostate Cancer"},
        {"value": "colorectal", "label": "Colorectal Cancer"},
        {"value": "melanoma", "label": "Melanoma"},
        {"value": "other", "label": "Other"},
    ],
    "common_conditions": [
        {"value": "diabetes", "label": "Diabetes"},
        {"value": "hypertension", "label": "Hypertension"},
        {"value": "asthma", "label": "Asthma"},
        {"value": "copd", "label": "COPD"},
        {"value": "heart_disease", "label": "Heart disease"},
        {"value": "hypothyroidism", "label": "Hypothyroidism"},
        {"value": "depression_anxiety", "label": "Depression or anxiety"},
        {"value": "arthritis", "label": "Arthritis"},
        {"value": "ibs_crohns", "label": "IBS or Crohn's"},
        {"value": "ms", "label": "Multiple Sclerosis"},
        {"value": "lupus", "label": "Lupus"},
        {"value": "kidney_disease", "label": "Kidney disease"},
    ],
    "smoking_status": [
        {"value": "never", "label": "Never"},
        {"value": "former", "label": "Former"},
        {"value": "occasional", "label": "Occasional"},
        {"value": "daily", "label": "Daily"},
    ],
    "alcohol_frequency": [
        {"value": "none", "label": "None"},
        {"value": "rarely", "label": "Rarely"},
        {"value": "socially", "label": "Socially"},
        {"value": "weekly", "label": "Weekly"},
        {"value": "daily", "label": "Daily"},
    ],
    "exercise_level": [
        {"value": "sedentary", "label": "Sedentary"},
        {"value": "light", "label": "Light"},
        {"value": "moderate", "label": "Moderate"},
        {"value": "active", "label": "Active"},
    ],
    "diet_type": [
        {"value": "omnivore", "label": "Omnivore"},
        {"value": "vegetarian", "label": "Vegetarian"},
        {"value": "vegan", "label": "Vegan"},
        {"value": "keto", "label": "Keto"},
        {"value": "gluten_free", "label": "Gluten-free"},
    ],
    "family_relatives": [
        {"value": "mother", "label": "Mother"},
        {"value": "father", "label": "Father"},
        {"value": "maternal_grandparent", "label": "Maternal grandparent"},
        {"value": "paternal_grandparent", "label": "Paternal grandparent"},
        {"value": "sibling", "label": "Sibling"},
    ],
    "family_conditions": [
        {"value": "heart_disease", "label": "Heart disease"},
        {"value": "diabetes", "label": "Diabetes"},
        {"value": "cancer", "label": "Cancer"},
        {"value": "stroke", "label": "Stroke"},
        {"value": "alzheimers", "label": "Alzheimer's"},
        {"value": "mental_health", "label": "Mental health"},
        {"value": "kidney_disease", "label": "Kidney disease"},
    ],
    "ecog_performance_status": [
        {"value": 0, "label": "0 — Fully active"},
        {"value": 1, "label": "1 — Some symptoms but ambulatory"},
        {"value": 2, "label": "2 — Limited activity, in bed less than 50%"},
        {"value": 3, "label": "3 — Limited self-care, in bed more than 50%"},
        {"value": 4, "label": "4 — Completely disabled"},
    ],
    "iss_stage": [
        {"value": "i", "label": "Stage I"},
        {"value": "ii", "label": "Stage II"},
        {"value": "iii", "label": "Stage III"},
        {"value": "unknown", "label": "Unknown"},
    ],
    "myeloma_disease_status": [
        {"value": "newly_diagnosed", "label": "Newly diagnosed"},
        {"value": "relapsed", "label": "Relapsed"},
        {"value": "refractory", "label": "Refractory"},
        {"value": "remission", "label": "Remission"},
    ],
}
