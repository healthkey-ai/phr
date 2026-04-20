"""
Integration tests for the full Phase 2c extraction pipeline.

Real components: rasteriser, matching, models, Celery task (eager mode).
Mocked:          anthropic client.

Shape of coverage:
  - happy path: upload with 1 PDF → parsed_results populated with resolved identities
  - refusal: Claude declines → upload.status=failed with refusal copy
  - empty extraction: Claude returns [] → upload.status=completed with parsed_results=[]
  - invalid LOINC in LLM output falls through to name_fallback
  - multi-page PDF triggers paged mode with merge
  - LAB_UPLOAD_ENABLED=False returns 403
"""
import io
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF — build synthetic PDFs
import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.labs.models import LabTestType, LabUpload


@dataclass
class _TextBlock:
    type: str
    text: str


@dataclass
class _MockResponse:
    content: list


def _mock_response(text: str) -> _MockResponse:
    return _MockResponse(content=[_TextBlock(type="text", text=text)])


def _build_pdf(page_count: int = 1) -> bytes:
    """Minimal synthetic PDF in memory."""
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"Test page {i + 1}")
    buf = doc.write()
    doc.close()
    return buf


def _pdf_upload_file(name: str, page_count: int = 1) -> io.BytesIO:
    body = _build_pdf(page_count)
    f = io.BytesIO(body)
    f.name = name
    return f


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def catalog(db):
    call_command("loaddata", "lab_catalog.json", app_label="labs", verbosity=0)


@pytest.fixture
def user(db):
    return User.objects.create_user(email="sarah@example.com", password="Strong-Pass-123!")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture(autouse=True)
def _isolated_llm_env(settings):
    """Pin provider to claude + null both keys, same as test_llm_parser.py.
    Prevents tests from silently hitting a real API when the developer's .env
    has LAB_LLM_PROVIDER=openai set.

    Also force Celery eager mode so `.delay()` runs tasks inline regardless
    of CELERY_BROKER_URL in the developer's .env."""
    settings.LAB_LLM_PROVIDER = "claude"
    settings.ANTHROPIC_API_KEY = ""
    settings.OPENAI_API_KEY = ""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


def _mock_client(responses):
    client = MagicMock()
    iterator = iter(responses)

    def _create(**kwargs):
        nxt = next(iterator)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    client.messages.create.side_effect = _create
    return client


# ── Happy path ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPipelineHappyPath:
    def test_single_pdf_full_pipeline(self, client, catalog, settings):
        """Upload a 1-page PDF. Claude (mocked) returns 2 rows with valid
        LOINCs. Pipeline resolves identity, populates parsed_results, status
        flips to completed."""
        settings.ANTHROPIC_API_KEY = "sk-fake"

        claude_json = (
            '[{"test_name":"Hemoglobin","value":"12.5","unit":"g/dL",'
            '"reference_min":12.0,"reference_max":15.5,'
            '"measured_date":"2026-03-15","page":0,"confidence":0.95,'
            '"loinc_code":"718-7","loinc_name":"Hemoglobin in Blood",'
            '"loinc_default_unit":"g/dL"},'
            '{"test_name":"WBC","value":"7.2","unit":"10^3/uL",'
            '"reference_min":4.5,"reference_max":11.0,'
            '"measured_date":"2026-03-15","page":0,"confidence":0.93,'
            '"loinc_code":"6690-2","loinc_name":"WBC count","loinc_default_unit":"10^3/uL"}]'
        )
        mock_cli = _mock_client([_mock_response(claude_json)])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("cbc.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f, "lab_date": "2026-03-15"},
                format="multipart",
            )

        assert response.status_code == 202, response.content
        body = response.json()
        assert body["status"] == "completed"
        assert body["provider"] == "claude"
        assert len(body["parsed_results"]) == 2

        hgb_row = next(r for r in body["parsed_results"] if r["raw_loinc_code"] == "718-7")
        assert hgb_row["matched_test_abbreviation"] == "hgb"
        assert hgb_row["match_method"] == "loinc"
        assert hgb_row["accepted"] is None  # pending patient review
        assert hgb_row["measured_date"] == "2026-03-15"

    def test_name_fallback_for_invalid_loinc(self, client, catalog, settings):
        """Claude returns a made-up LOINC code. Matcher validates it against
        loinc_common.json, finds no hit, falls back to name match. The
        existing 'Hemoglobin' row is found via name_normalized."""
        settings.ANTHROPIC_API_KEY = "sk-fake"

        claude_json = (
            '[{"test_name":"Hemoglobin","value":"12.5","unit":"g/dL",'
            '"confidence":0.9,"loinc_code":"99999-9","loinc_name":"Fake"}]'
        )
        mock_cli = _mock_client([_mock_response(claude_json)])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("cbc.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )

        body = response.json()
        assert len(body["parsed_results"]) == 1
        row = body["parsed_results"][0]
        assert row["match_method"] == "name_fallback"
        assert row["matched_test_abbreviation"] == "hgb"
        # The raw LOINC is preserved for audit even though it was discarded
        assert row["raw_loinc_code"] == "99999-9"

    def test_novel_test_auto_creates_labtesttype(self, client, catalog, settings):
        """Claude returns a test not in our curated catalog but WITH a valid
        LOINC from loinc_common.json. Pipeline auto-creates the LabTestType."""
        settings.ANTHROPIC_API_KEY = "sk-fake"

        # Ferritin: in loinc_common.json but NOT in lab_catalog.json
        before = LabTestType.objects.filter(loinc_code="2276-4").count()
        assert before == 0

        claude_json = (
            '[{"test_name":"Ferritin","value":"150","unit":"ng/mL",'
            '"confidence":0.92,"loinc_code":"2276-4",'
            '"loinc_name":"Ferritin","loinc_default_unit":"ng/mL"}]'
        )
        mock_cli = _mock_client([_mock_response(claude_json)])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("ferritin.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )

        body = response.json()
        assert body["parsed_results"][0]["match_method"] == "loinc"
        # LabTestType row now exists
        assert LabTestType.objects.filter(loinc_code="2276-4").count() == 1


# ── Failure paths ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPipelineFailures:
    def test_claude_refusal_fails_upload(self, client, catalog, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        mock_cli = _mock_client([_mock_response(
            "I apologize, but I cannot process this image. It appears to contain personal medical information."
        )])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("cbc.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )

        body = response.json()
        assert body["status"] == "failed"
        assert "enter the values manually" in body["error_message"].lower()

    def test_empty_extraction_completes(self, client, catalog, settings):
        """Claude returns []. Upload completes with empty parsed_results."""
        settings.ANTHROPIC_API_KEY = "sk-fake"
        mock_cli = _mock_client([_mock_response("[]")])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("blank.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )

        body = response.json()
        assert body["status"] == "completed"
        assert body["parsed_results"] == []

    def test_missing_api_key_fails_cleanly(self, client, catalog, settings):
        settings.ANTHROPIC_API_KEY = ""  # simulate prod-without-key misconfig

        f = _pdf_upload_file("cbc.pdf")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f},
            format="multipart",
        )

        body = response.json()
        assert body["status"] == "failed"
        # Generic LLM-error copy (not the raw stack trace)
        assert "trouble reading" in body["error_message"].lower()


# ── Feature flag ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFeatureFlag:
    def test_flag_disabled_returns_403(self, client, catalog, settings):
        settings.LAB_UPLOAD_ENABLED = False

        f = _pdf_upload_file("cbc.pdf")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f},
            format="multipart",
        )
        assert response.status_code == 403
        assert "not yet available" in str(response.content).lower()

    def test_flag_enabled_works(self, client, catalog, settings):
        settings.LAB_UPLOAD_ENABLED = True
        settings.ANTHROPIC_API_KEY = "sk-fake"

        mock_cli = _mock_client([_mock_response("[]")])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("cbc.pdf")
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )
        assert response.status_code == 202


# ── Paged extraction ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPagedExtraction:
    def test_12_page_pdf_triggers_two_batches(self, client, catalog, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"

        # Two batches → two Claude calls → return one distinct row each
        mock_cli = _mock_client([
            _mock_response('[{"test_name":"Hemoglobin","value":"12.5","unit":"g/dL","loinc_code":"718-7"}]'),
            _mock_response('[{"test_name":"WBC","value":"7.2","unit":"10^3/uL","loinc_code":"6690-2"}]'),
        ])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=mock_cli):
            f = _pdf_upload_file("big.pdf", page_count=12)
            response = client.post(
                reverse("lab-upload-list"),
                data={"files": f},
                format="multipart",
            )

        body = response.json()
        assert body["status"] == "completed"
        # Each batch returned a unique row → 2 rows after merge
        names = {r["raw_name"] for r in body["parsed_results"]}
        assert names == {"Hemoglobin", "WBC"}
        # Exactly 2 Claude calls
        assert mock_cli.messages.create.call_count == 2
