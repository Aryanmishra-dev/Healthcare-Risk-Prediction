"""
Views for the healthcare risk prediction UI.
"""

import os

import requests
from django.shortcuts import render

FASTAPI_BASE = os.environ.get("FASTAPI_BASE_URL", "http://127.0.0.1:8000")


def _clamp(value, lo, hi):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def predict_view(request):
    """Handle diabetes, heart disease, and lung cancer prediction forms."""
    context = {
        "diabetes_result": None,
        "diabetes_error": None,
        "diabetes_form": None,
        "heart_result": None,
        "heart_error": None,
        "heart_form": None,
        "lung_result": None,
        "lung_error": None,
        "lung_form": None,
    }

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "diabetes":
            _handle_diabetes(request, context)
        elif form_type == "heart":
            _handle_heart_disease(request, context)
        elif form_type == "lung":
            _handle_lung_cancer(request, context)

    return render(request, "predict.html", context)


def _handle_diabetes(request, context):
    """Process diabetes prediction form."""
    try:
        payload = {
            "age": _clamp(float(request.POST.get("age", 7)), 1, 13),
            "bmi": _clamp(float(request.POST.get("bmi", 25)), 10, 80),
            "bp": _clamp(float(request.POST.get("bp", 0)), 0, 1),
            "cholesterol": _clamp(float(request.POST.get("cholesterol", 0)), 0, 1),
            "smoker": _clamp(float(request.POST.get("smoker", 0)), 0, 1),
            "activity": _clamp(float(request.POST.get("activity", 1)), 0, 1),
            "health": _clamp(float(request.POST.get("health", 3)), 1, 5),
            "mental": _clamp(float(request.POST.get("mental", 0)), 0, 30),
        }
        response = requests.post(f"{FASTAPI_BASE}/predict", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        context["diabetes_result"] = result
        context["diabetes_form"] = payload
        pct = float(result.get("risk_percentage", 0))
        context["diabetes_gauge_offset"] = round(251.2 - 188.4 * pct / 100, 1)
    except requests.exceptions.ConnectionError:
        context["diabetes_error"] = "Cannot connect to the prediction API. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.RequestException as e:
        context["diabetes_error"] = f"API request failed: {e}"
    except (ValueError, TypeError) as e:
        context["diabetes_error"] = f"Invalid input: {e}"


def _handle_heart_disease(request, context):
    """Process heart disease prediction form."""
    try:
        payload = {
            "age": _clamp(float(request.POST.get("hd_age", 7)), 1, 13),
            "sex": _clamp(int(request.POST.get("hd_sex", 1)), 0, 1),
            "bmi": _clamp(float(request.POST.get("hd_bmi", 25)), 10, 80),
            "high_bp": _clamp(int(request.POST.get("hd_high_bp", 0)), 0, 1),
            "high_chol": _clamp(int(request.POST.get("hd_high_chol", 0)), 0, 1),
            "smoker": _clamp(int(request.POST.get("hd_smoker", 0)), 0, 1),
            "phys_activity": _clamp(int(request.POST.get("hd_phys_activity", 1)), 0, 1),
            "fruits": _clamp(int(request.POST.get("hd_fruits", 1)), 0, 1),
            "veggies": _clamp(int(request.POST.get("hd_veggies", 1)), 0, 1),
            "heavy_drinker": _clamp(int(request.POST.get("hd_heavy_drinker", 0)), 0, 1),
            "gen_health": _clamp(int(request.POST.get("hd_gen_health", 3)), 1, 5),
            "ment_health": _clamp(int(request.POST.get("hd_ment_health", 0)), 0, 30),
            "phys_health": _clamp(int(request.POST.get("hd_phys_health", 0)), 0, 30),
            "diabetes": _clamp(int(request.POST.get("hd_diabetes", 0)), 0, 1),
        }
        response = requests.post(f"{FASTAPI_BASE}/predict-heart", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        context["heart_result"] = result
        context["heart_form"] = payload
        pct = float(result.get("risk_percentage", 0))
        context["heart_gauge_offset"] = round(251.2 - 188.4 * pct / 100, 1)
    except requests.exceptions.ConnectionError:
        context["heart_error"] = "Cannot connect to the prediction API. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.RequestException as e:
        context["heart_error"] = f"API request failed: {e}"
    except (ValueError, TypeError) as e:
        context["heart_error"] = f"Invalid input: {e}"


def _handle_lung_cancer(request, context):
    """Process lung cancer prediction form."""
    try:
        payload = {
            "age": _clamp(int(request.POST.get("lc_age", 50)), 18, 100),
            "gender": _clamp(int(request.POST.get("lc_gender", 1)), 0, 1),
            "smoking": _clamp(int(request.POST.get("lc_smoking", 0)), 0, 1),
            "yellow_fingers": _clamp(int(request.POST.get("lc_yellow_fingers", 0)), 0, 1),
            "chronic_disease": _clamp(int(request.POST.get("lc_chronic_disease", 0)), 0, 1),
            "fatigue": _clamp(int(request.POST.get("lc_fatigue", 0)), 0, 1),
            "wheezing": _clamp(int(request.POST.get("lc_wheezing", 0)), 0, 1),
            "shortness_of_breath": _clamp(int(request.POST.get("lc_shortness_of_breath", 0)), 0, 1),
        }
        response = requests.post(f"{FASTAPI_BASE}/predict-lung", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        context["lung_result"] = result
        context["lung_form"] = payload
        pct = float(result.get("risk_percentage", 0))
        context["lung_gauge_offset"] = round(251.2 - 188.4 * pct / 100, 1)
    except requests.exceptions.ConnectionError:
        context["lung_error"] = "Cannot connect to the prediction API. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.RequestException as e:
        context["lung_error"] = f"API request failed: {e}"
    except (ValueError, TypeError) as e:
        context["lung_error"] = f"Invalid input: {e}"
