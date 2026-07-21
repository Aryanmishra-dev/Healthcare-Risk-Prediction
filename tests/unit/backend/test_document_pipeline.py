"""
Tests for the medical document AI pipeline.

Covers:
  - File validation (MIME types, size limits)
  - Medical NLP entity extraction
  - Feature mapping (diabetes, heart, lung)
  - Upload endpoint integration
"""

import io
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.services.feature_mapper import (
    map_to_all_models,
    map_to_diabetes_features,
    map_to_heart_features,
    map_to_lung_features,
)
from backend.app.services.medical_nlp import extract_clinical_entities
from backend.app.utils.file_validation import (
    MAX_FILE_SIZE_BYTES,
    sanitize_filename,
    validate_mime_type,
)

VALID_API_KEY = os.environ.get("DEV_API_KEY", "test-dev-api-key")


# ══════════════════════════════════════════════════════════════════════════
#  File Validation Tests
# ══════════════════════════════════════════════════════════════════════════


class TestFileValidation:

    def test_valid_pdf_mime(self):
        assert (
            validate_mime_type("application/pdf", "report.pdf")
            == "application/pdf"
        )

    def test_valid_jpeg_mime(self):
        assert validate_mime_type("image/jpeg", "scan.jpg") == "image/jpeg"

    def test_valid_png_mime(self):
        assert validate_mime_type("image/png", "scan.png") == "image/png"

    def test_invalid_mime_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_mime_type("text/plain", "notes.txt")
        assert exc_info.value.status_code == 400

    def test_fallback_to_extension(self):
        # Content-type is octet-stream but filename has .pdf extension
        result = validate_mime_type("application/octet-stream", "report.pdf")
        assert result == "application/pdf"

    def test_sanitize_filename_basic(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_sanitize_filename_path_stripped(self):
        result = sanitize_filename("/etc/passwd/../../../evil.pdf")
        assert "/" not in result
        assert result.endswith(".pdf")

    def test_sanitize_filename_special_chars(self):
        result = sanitize_filename("Dr. Smith's report (2024).pdf")
        assert "'" not in result
        assert "(" not in result

    def test_sanitize_filename_empty(self):
        assert sanitize_filename("") == "unnamed_upload"


# ══════════════════════════════════════════════════════════════════════════
#  Medical NLP Tests
# ══════════════════════════════════════════════════════════════════════════


class TestMedicalNLP:

    def test_extract_bmi(self):
        text = "Patient BMI 27.4, blood tests normal."
        entities = extract_clinical_entities(text)
        assert entities["bmi"]["value"] == 27.4

    def test_extract_bmi_with_colon(self):
        text = "BMI: 32.1"
        entities = extract_clinical_entities(text)
        assert entities["bmi"]["value"] == 32.1

    def test_extract_bmi_body_mass_index(self):
        text = "Body mass index of 29.5"
        entities = extract_clinical_entities(text)
        assert entities["bmi"]["value"] == 29.5

    def test_extract_blood_pressure_numeric_high(self):
        text = "BP 150/95 mmHg, patient reports headaches."
        entities = extract_clinical_entities(text)
        assert entities["blood_pressure"]["value"] == "high"

    def test_extract_blood_pressure_numeric_normal(self):
        text = "Blood pressure 120/80."
        entities = extract_clinical_entities(text)
        assert entities["blood_pressure"]["value"] == "normal"

    def test_extract_blood_pressure_keyword(self):
        text = "Patient has high blood pressure."
        entities = extract_clinical_entities(text)
        assert entities["blood_pressure"]["value"] == "high"

    def test_extract_blood_pressure_hypertension(self):
        text = "Diagnosis: hypertension stage 2."
        entities = extract_clinical_entities(text)
        assert entities["blood_pressure"]["value"] == "high"

    def test_extract_cholesterol_high_keyword(self):
        text = "High cholesterol noted."
        entities = extract_clinical_entities(text)
        assert entities["cholesterol"]["value"] == "high"

    def test_extract_cholesterol_numeric_high(self):
        text = "Total cholesterol 260 mg/dL."
        entities = extract_clinical_entities(text)
        assert entities["cholesterol"]["value"] == "high"

    def test_extract_cholesterol_numeric_normal(self):
        text = "Cholesterol 180."
        entities = extract_clinical_entities(text)
        assert entities["cholesterol"]["value"] == "normal"

    def test_extract_smoker_yes(self):
        text = "Patient is a current smoker, 10 pack-years."
        entities = extract_clinical_entities(text)
        assert entities["smoking"]["value"] == "yes"

    def test_extract_smoker_no(self):
        text = "Non-smoker, no tobacco use."
        entities = extract_clinical_entities(text)
        assert entities["smoking"]["value"] == "no"

    def test_extract_physical_activity_active(self):
        text = "Patient exercises regularly, 30 min/day."
        entities = extract_clinical_entities(text)
        assert entities["physical_activity"]["value"] == "active"

    def test_extract_physical_activity_sedentary(self):
        text = "Sedentary lifestyle, office worker."
        entities = extract_clinical_entities(text)
        assert entities["physical_activity"]["value"] == "inactive"

    def test_extract_general_health(self):
        text = "General health: good."
        entities = extract_clinical_entities(text)
        assert entities["general_health"]["value"] == 3

    def test_extract_general_health_excellent(self):
        text = "Overall health: excellent."
        entities = extract_clinical_entities(text)
        assert entities["general_health"]["value"] == 1

    def test_extract_mental_health_days(self):
        text = "Mental health days: 5 in the past month."
        entities = extract_clinical_entities(text)
        assert entities["mental_health"]["value"] == 5

    def test_extract_age(self):
        text = "Patient age 52, presenting with chest pain."
        entities = extract_clinical_entities(text)
        assert entities["age"]["value"] == 52

    def test_extract_age_years_old(self):
        text = "65 year old male patient."
        entities = extract_clinical_entities(text)
        assert entities["age"]["value"] == 65

    def test_extract_gender_male(self):
        text = "Sex: Male. Age: 45."
        entities = extract_clinical_entities(text)
        assert entities["gender"]["value"] == "male"

    def test_extract_gender_female(self):
        text = "Gender: Female, age 38."
        entities = extract_clinical_entities(text)
        assert entities["gender"]["value"] == "female"

    def test_extract_blood_group(self):
        text = "Blood group: O+"
        entities = extract_clinical_entities(text)
        assert entities["blood_group"]["value"] == "O+"

    def test_extract_blood_group_negative(self):
        text = "Type: AB negative"
        entities = extract_clinical_entities(text)
        assert entities["blood_group"]["value"] == "AB-"

    def test_extract_medical_history(self):
        text = "Medical history: Patient has a history of asthma.\nDiagnosis:"
        entities = extract_clinical_entities(text)
        assert (
            entities["medical_history"]["value"]
            == "Patient has a history of asthma."
        )

    def test_extract_diagnosis(self):
        text = "Diagnosis: Type 2 Diabetes Mellitus\nMedications:"
        entities = extract_clinical_entities(text)
        assert entities["diagnosis"]["value"] == "Type 2 Diabetes Mellitus"

    def test_extract_medications(self):
        text = "Medications: Metformin 500mg BID\n"
        entities = extract_clinical_entities(text)
        assert entities["medications"]["value"] == "Metformin 500mg BID"

    def test_extract_none_values(self):
        text = "The weather is sunny today."
        entities = extract_clinical_entities(text)
        assert entities["bmi"] is None
        assert entities["blood_pressure"] is None
        assert entities["blood_group"] is None

    def test_full_medical_report(self):
        """Test extraction from a realistic medical report snippet."""
        text = """
        Patient: John Doe, 58 years old, Male
        Blood Type: A+
        BMI: 31.2
        Blood Pressure: 145/92 (elevated)
        Cholesterol: 255 mg/dL
        Smoking: No, never smoked
        Physical activity: sedentary
        General health: fair
        Mental health: 8 days of poor mental health in past 30 days
        
        Medical History:
        Hypertension, hyperlipidemia.
        
        Diagnosis:
        Coronary artery disease.
        
        Medications:
        Lisinopril, Atorvastatin.
        """
        entities = extract_clinical_entities(text)
        assert entities["age"]["value"] == 58
        assert entities["gender"]["value"] == "male"
        assert entities["blood_group"]["value"] == "A+"
        assert entities["bmi"]["value"] == 31.2
        assert entities["blood_pressure"]["value"] == "high"
        assert entities["cholesterol"]["value"] == "high"
        assert entities["smoking"]["value"] == "no"
        assert entities["physical_activity"]["value"] == "inactive"
        assert entities["general_health"]["value"] == 4
        assert entities["mental_health"]["value"] == 8
        assert (
            entities["medical_history"]["value"]
            == "Hypertension, hyperlipidemia."
        )
        assert entities["diagnosis"]["value"] == "Coronary artery disease."
        assert entities["medications"]["value"] == "Lisinopril, Atorvastatin."


# ══════════════════════════════════════════════════════════════════════════
#  Feature Mapper Tests
# ══════════════════════════════════════════════════════════════════════════


class TestFeatureMapper:

    @pytest.fixture
    def sample_entities(self):
        return {
            "bmi": {"value": 27.4, "confidence": 1.0},
            "blood_pressure": {"value": "high", "confidence": 1.0},
            "cholesterol": {"value": "normal", "confidence": 1.0},
            "smoking": {"value": "no", "confidence": 1.0},
            "physical_activity": {"value": "active", "confidence": 1.0},
            "general_health": {"value": 3, "confidence": 1.0},
            "mental_health": {"value": 5, "confidence": 1.0},
            "age": {"value": 52, "confidence": 1.0},
            "gender": {"value": "male", "confidence": 1.0},
        }

    def test_diabetes_mapping(self, sample_entities):
        result = map_to_diabetes_features(sample_entities)
        assert result["bmi"]["value"] == 27.4
        assert result["bp"]["value"] == 1.0  # "high" → 1
        assert result["cholesterol"]["value"] == 0.0  # "normal" → 0
        assert result["smoker"]["value"] == 0.0  # "no" → 0
        assert result["activity"]["value"] == 1.0  # "active" → 1
        assert result["health"]["value"] == 3.0
        assert result["mental"]["value"] == 5.0
        assert result["age"]["value"] == 7.0  # 52 → group 7 (50-54)

    def test_heart_mapping(self, sample_entities):
        result = map_to_heart_features(sample_entities)
        assert result["hd_bmi"]["value"] == 27.4
        assert result["hd_sex"]["value"] == 1  # "male" → 1
        assert result["hd_high_bp"]["value"] == 1
        assert result["hd_high_chol"]["value"] == 0
        assert result["hd_smoker"]["value"] == 0

    def test_lung_mapping(self, sample_entities):
        result = map_to_lung_features(sample_entities)
        assert result["lc_age"]["value"] == 52
        assert result["lc_gender"]["value"] == 1
        assert result["lc_smoking"]["value"] == 0

    def test_map_all_models(self, sample_entities):
        result = map_to_all_models(sample_entities)
        assert "diabetes" in result
        assert "heart" in result
        assert "lung" in result

    def test_empty_entities_returns_empty(self):
        """All None entities should produce NO mapped features so UI isn't overwritten."""
        entities = {
            k: None
            for k in [
                "bmi",
                "blood_pressure",
                "cholesterol",
                "smoking",
                "physical_activity",
                "general_health",
                "mental_health",
                "age",
                "gender",
                "blood_group",
                "medical_history",
                "diagnosis",
                "medications",
            ]
        }
        d = map_to_diabetes_features(entities)
        assert d == {}

    def test_age_group_mapping(self):
        """Test age-to-group conversion for various ages."""
        from backend.app.services.feature_mapper import _age_to_group

        assert _age_to_group(20) == 1.0
        assert _age_to_group(30) == 3.0
        assert _age_to_group(55) == 8.0
        assert _age_to_group(80) == 13.0
        assert _age_to_group(None) == 7.0  # default


# ══════════════════════════════════════════════════════════════════════════
#  Upload Endpoint Integration Test
# ══════════════════════════════════════════════════════════════════════════

from backend.app.main import app, verify_csrf_token


class TestUploadEndpoint:
    @pytest.fixture(autouse=True)
    def bypass_csrf(self):
        app.dependency_overrides[verify_csrf_token] = lambda: "test-token"
        yield
        app.dependency_overrides.clear()

    def test_upload_rejects_invalid_type(self, client):
        """Text files should be rejected."""
        fake_file = io.BytesIO(b"Hello, world!")
        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("test.txt", fake_file, "text/plain")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 400

    def test_upload_rejects_oversized(self, client):
        """Files > 5 MB should be rejected."""
        fake_file = io.BytesIO(b"x" * (MAX_FILE_SIZE_BYTES + 1))
        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("big.pdf", fake_file, "application/pdf")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 400

    def test_upload_rejects_empty(self, client):
        """Empty files should be rejected."""
        fake_file = io.BytesIO(b"")
        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("empty.pdf", fake_file, "application/pdf")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 400

    @patch("backend.app.api.v1.routes.upload.parse_document")
    def test_upload_with_mocked_parser(self, mock_parse, client):
        """Test full pipeline with mocked document parser."""
        mock_parse.return_value = (
            "Patient age 55, Male. BMI: 28.5. "
            "Blood pressure: high. Cholesterol: normal. "
            "Non-smoker. Physically active. General health: good."
        )
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content bytes here")

        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("report.pdf", fake_pdf, "application/pdf")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "entities" in data
        assert "mapped_features" in data
        assert data["entities"]["bmi"]["value"] == 28.5
        assert data["entities"]["blood_pressure"]["value"] == "high"
        assert data["entities"]["smoking"]["value"] == "no"
        assert data["mapped_features"]["diabetes"]["bmi"]["value"] == 28.5

    @patch("backend.app.api.v1.routes.upload.parse_document")
    def test_upload_parse_failure_returns_422(self, mock_parse, client):
        """When parse_document raises, endpoint returns 422."""
        mock_parse.side_effect = Exception("Corrupt file")
        fake_file = io.BytesIO(b"%PDF-1.4 corrupted")
        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("bad.pdf", fake_file, "application/pdf")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 422
        assert "Failed to extract text" in resp.json()["detail"]

    @patch("backend.app.api.v1.routes.upload.parse_document")
    def test_upload_no_text_returns_warning(self, mock_parse, client):
        """When parse_document returns empty string, endpoint returns warning."""
        mock_parse.return_value = ""
        fake_file = io.BytesIO(b"%PDF-1.4 blank")
        resp = client.post(
            "/api/v1/document/upload",
            files={"file": ("blank.pdf", fake_file, "application/pdf")},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "warning" in data
        assert "No text could be extracted" in data["warning"]

    def test_text_extraction_endpoint_valid(self, client):
        """POST /api/v1/document/text with valid input returns entities."""
        resp = client.post(
            "/api/v1/document/text",
            json={"text": "Patient age 45, BMI 28.5, non-smoker."},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "mapped_features" in data
        assert "raw_text" in data

    def test_text_extraction_endpoint_empty(self, client):
        """POST /api/v1/document/text with empty text returns 422 or error."""
        resp = client.post(
            "/api/v1/document/text",
            json={"text": ""},
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
