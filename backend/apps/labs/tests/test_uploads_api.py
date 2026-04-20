"""
API tests for Phase 2b upload endpoints.

Scope: upload API surface — multipart parsing, size/MIME/count caps, SHA256
dedup, IsOwner enforcement, and the task-dispatch handoff. The real extraction
pipeline (rasteriser + Claude) is mocked at the module level via an
autouse fixture below — end-to-end pipeline tests live in test_pipeline.py.
"""
import io
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.labs.models import LabUpload, LabUploadFile, LabUploadStatus


@pytest.fixture(autouse=True)
def _stub_extraction_pipeline():
    """Replace the real pipeline with an empty-result stub for all tests in
    this module. Tests here verify the UPLOAD API, not extraction — and the
    minimal magic-byte test files aren't real PDFs that PyMuPDF can parse."""
    with patch(
        "apps.labs.tasks._run_extraction_pipeline",
        return_value=[],
    ):
        yield


# ── Magic-byte prefixes we use to construct valid-looking test files ─────────

PDF_MAGIC = b"%PDF-1.4\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 20
HEIC_MAGIC = b"\x00\x00\x00\x20ftypheic" + b"\x00" * 16


def _make_file(name: str, magic: bytes = PDF_MAGIC, size: int = 128, content: bytes | None = None):
    """Construct an in-memory file with the given magic-byte prefix + padding."""
    body = content if content is not None else magic + b"\x00" * max(0, size - len(magic))
    f = io.BytesIO(body)
    f.name = name
    return f


@pytest.fixture
def user(db):
    return User.objects.create_user(email="sarah@example.com", password="Strong-Pass-123!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="intruder@example.com", password="Strong-Pass-123!")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def other_client(other_user):
    c = APIClient()
    c.force_authenticate(user=other_user)
    return c


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUploadCreate:
    def test_single_pdf_uploads_and_completes(self, client):
        """202 on create, completed status after the eager stub task runs."""
        f = _make_file("cbc.pdf")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f, "lab_date": "2026-03-15", "notes": "Annual CBC"},
            format="multipart",
        )
        assert response.status_code == 202, response.content

        body = response.json()
        assert body["status"] == "completed"  # eager mode — task already ran
        assert body["parsed_results"] == []   # Phase 2b stub leaves it empty
        assert body["lab_date"] == "2026-03-15"
        assert body["notes"] == "Annual CBC"
        assert len(body["files"]) == 1
        assert body["files"][0]["original_filename"] == "cbc.pdf"
        assert body["files"][0]["mime_type"] == "application/pdf"
        assert len(body["files"][0]["sha256"]) == 64  # hex digest

        # Celery task id was stamped
        assert body["celery_task_id"]

    def test_multiple_files_accepted(self, client):
        """Multi-file upload keeps order and hashes every file."""
        files = [
            _make_file("page1.pdf"),
            _make_file("page2.pdf", content=PDF_MAGIC + b"different"),
            _make_file("supplement.png", magic=PNG_MAGIC),
        ]
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": files},
            format="multipart",
        )
        assert response.status_code == 202, response.content
        body = response.json()
        assert len(body["files"]) == 3
        assert [f["file_order"] for f in body["files"]] == [0, 1, 2]
        assert {f["mime_type"] for f in body["files"]} == {"application/pdf", "image/png"}

    def test_jpeg_and_heic_accepted(self, client):
        f_jpeg = _make_file("scan.jpg", magic=JPEG_MAGIC)
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f_jpeg},
            format="multipart",
        )
        assert response.status_code == 202

        f_heic = _make_file("photo.heic", magic=HEIC_MAGIC)
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f_heic},
            format="multipart",
        )
        assert response.status_code == 202


# ── Dedup ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDedup:
    def test_single_file_reupload_returns_existing_session(self, client):
        f1 = _make_file("cbc.pdf")
        first = client.post(reverse("lab-upload-list"), data={"files": f1}, format="multipart")
        assert first.status_code == 202
        first_id = first.json()["id"]

        # Upload the same bytes again — should return the same row with 200.
        f2 = _make_file("cbc.pdf")  # same content
        second = client.post(reverse("lab-upload-list"), data={"files": f2}, format="multipart")
        assert second.status_code == 200, second.content
        assert second.json()["id"] == first_id

        # Confirm only one LabUpload row was created.
        assert LabUpload.objects.count() == 1

    def test_different_content_creates_new_session(self, client):
        f1 = _make_file("cbc.pdf", content=PDF_MAGIC + b"one")
        r1 = client.post(reverse("lab-upload-list"), data={"files": f1}, format="multipart")
        assert r1.status_code == 202

        f2 = _make_file("cbc.pdf", content=PDF_MAGIC + b"two")  # same name, different bytes
        r2 = client.post(reverse("lab-upload-list"), data={"files": f2}, format="multipart")
        assert r2.status_code == 202
        assert r2.json()["id"] != r1.json()["id"]

    def test_dedup_respects_user_scope(self, client, other_client):
        """Same file bytes from a different user = new session (no leak)."""
        shared_bytes = PDF_MAGIC + b"same-file-different-owner"

        f_owner = _make_file("cbc.pdf", content=shared_bytes)
        r_owner = client.post(
            reverse("lab-upload-list"), data={"files": f_owner}, format="multipart"
        )
        assert r_owner.status_code == 202

        f_intruder = _make_file("cbc.pdf", content=shared_bytes)
        r_intruder = other_client.post(
            reverse("lab-upload-list"), data={"files": f_intruder}, format="multipart"
        )
        assert r_intruder.status_code == 202
        assert r_intruder.json()["id"] != r_owner.json()["id"]

    def test_dedup_skips_failed_prior_sessions(self, client):
        """A failed prior upload with the same hash should NOT short-circuit —
        the patient wants a retry, not to be handed back the failure."""
        f1 = _make_file("cbc.pdf")
        r1 = client.post(reverse("lab-upload-list"), data={"files": f1}, format="multipart")
        assert r1.status_code == 202
        first = LabUpload.objects.get(pk=r1.json()["id"])
        first.mark_failed("synthetic failure")

        f2 = _make_file("cbc.pdf")  # same bytes
        r2 = client.post(reverse("lab-upload-list"), data={"files": f2}, format="multipart")
        assert r2.status_code == 202
        assert r2.json()["id"] != first.id


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestValidation:
    def test_rejects_unsupported_mime(self, client):
        """A .txt file (or any non-PDF/JPEG/PNG/HEIC) is rejected."""
        f = _make_file("notes.txt", magic=b"hello world\n")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f},
            format="multipart",
        )
        assert response.status_code == 400
        assert "unsupported" in str(response.content).lower()

    def test_rejects_file_larger_than_10mb(self, client, settings):
        """One oversized file kills the whole request."""
        # Craft a 10MB+1 byte body with a valid PDF magic
        body = PDF_MAGIC + b"\x00" * (settings.LAB_UPLOAD_MAX_FILE_BYTES - len(PDF_MAGIC) + 1)
        f = _make_file("huge.pdf", content=body)
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": f},
            format="multipart",
        )
        assert response.status_code == 400
        assert "max" in str(response.content).lower()

    def test_rejects_total_over_20mb(self, client, settings):
        """Two 11MB files individually pass the per-file check but fail totals."""
        # Make the individual per-file cap bigger than the default 10MB so a
        # legitimate-shaped 11MB body isn't rejected on the per-file rule.
        settings.LAB_UPLOAD_MAX_FILE_BYTES = 12 * 1024 * 1024
        # Two 11MB files = 22MB > 20MB
        body = PDF_MAGIC + b"\x00" * (11 * 1024 * 1024 - len(PDF_MAGIC))
        f1 = _make_file("a.pdf", content=body)
        f2 = _make_file("b.pdf", content=body + b"diff")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": [f1, f2]},
            format="multipart",
        )
        assert response.status_code == 400
        assert "total" in str(response.content).lower()

    def test_rejects_more_than_max_files(self, client, settings):
        files = [_make_file(f"f{i}.pdf", content=PDF_MAGIC + bytes([i])) for i in range(settings.LAB_UPLOAD_MAX_FILES + 1)]
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": files},
            format="multipart",
        )
        assert response.status_code == 400

    def test_deduplicates_identical_content_within_request(self, client):
        """Two files with different names but identical bytes (common when a
        patient has 'report.pdf' and 'report (1).pdf' both in Downloads)
        get silently deduplicated — we save one row, not an error."""
        body = PDF_MAGIC + b"repeated"
        f1 = _make_file("one.pdf", content=body)
        f2 = _make_file("two.pdf", content=body)  # identical bytes, different name
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": [f1, f2]},
            format="multipart",
        )
        assert response.status_code == 202, response.content
        body = response.json()
        # Only one LabUploadFile row created — the duplicate was silently skipped
        assert len(body["files"]) == 1
        assert body["files"][0]["original_filename"] == "one.pdf"

    def test_keeps_distinct_files_within_request(self, client):
        """Sanity: two distinct payloads both land."""
        f1 = _make_file("one.pdf", content=PDF_MAGIC + b"first")
        f2 = _make_file("two.pdf", content=PDF_MAGIC + b"second")
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": [f1, f2]},
            format="multipart",
        )
        assert response.status_code == 202
        assert len(response.json()["files"]) == 2

    def test_empty_files_list_rejected(self, client):
        response = client.post(
            reverse("lab-upload-list"),
            data={"files": []},
            format="multipart",
        )
        assert response.status_code == 400


# ── Retrieve ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUploadRetrieve:
    def test_get_returns_full_serialized_upload(self, client):
        f = _make_file("cbc.pdf")
        create = client.post(reverse("lab-upload-list"), data={"files": f}, format="multipart")
        upload_id = create.json()["id"]

        response = client.get(reverse("lab-upload-detail", args=[upload_id]))
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == upload_id
        assert body["status"] == "completed"
        assert len(body["files"]) == 1

    def test_other_users_upload_404s(self, client, other_client):
        f = _make_file("cbc.pdf")
        create = client.post(reverse("lab-upload-list"), data={"files": f}, format="multipart")
        upload_id = create.json()["id"]

        response = other_client.get(reverse("lab-upload-detail", args=[upload_id]))
        assert response.status_code == 404

    def test_unauthenticated_blocked(self, db):
        f = _make_file("cbc.pdf")
        anon = APIClient()
        response = anon.post(reverse("lab-upload-list"), data={"files": f}, format="multipart")
        assert response.status_code == 401


# ── Task integration ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskDispatch:
    def test_stub_task_flips_to_completed(self, client):
        """In eager mode, the stub runs synchronously — the response body
        should already show status=completed with parsed_results=[]."""
        f = _make_file("cbc.pdf")
        response = client.post(reverse("lab-upload-list"), data={"files": f}, format="multipart")
        body = response.json()
        assert body["status"] == "completed"
        assert body["parsed_results"] == []
        assert body["completed_at"] is not None

    def test_task_failure_marks_upload_failed(self, client):
        """If the task raises, the except branch marks the upload failed
        with a user-facing message."""
        f = _make_file("cbc.pdf")

        # Patch out the body of process_lab_upload to raise.
        # We monkeypatch the mark_processing method so the body raises
        # inside the try block and the except branch catches it.
        with patch(
            "apps.labs.models.LabUpload.mark_processing",
            side_effect=RuntimeError("synthetic"),
        ):
            # Eager propagation is on — suppress via try/except at the caller
            # so the HTTP request still returns a response.
            try:
                client.post(
                    reverse("lab-upload-list"),
                    data={"files": f},
                    format="multipart",
                )
            except RuntimeError:
                pass

        # The upload row should exist with status=failed.
        upload = LabUpload.objects.first()
        assert upload is not None
        assert upload.status == LabUploadStatus.FAILED
        assert "went wrong" in upload.error_message.lower()
