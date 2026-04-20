"""
Tests for apps.labs.parsers.llm_parser.

Strategy: both anthropic and openai clients are replaced via monkeypatched
factory functions. No real API calls in CI. Cross-provider tests are
parametrized over the two providers so each path gets the same coverage.

Covers:
  - detect_refusal pattern matching (positive + negative)
  - _parse_response_json (clean JSON, fenced JSON, prose-wrapped, malformed)
  - _coerce_row defaults + numeric coercion + confidence clamping
  - extract_batch (both providers): happy path, refusal, parse error, missing key
  - extract: single-shot + paged merge
  - merge_results: dedup semantics
  - _resolve_provider: claude default, openai, unknown fallback
"""
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from apps.labs.parsers.llm_parser import (
    ExtractionError,
    ParseError,
    RefusalError,
    _coerce_row,
    _parse_response_json,
    _resolve_provider,
    detect_refusal,
    extract,
    extract_batch,
    merge_results,
)
from apps.labs.parsers.pdf_rasteriser import PageBatch, PageImage


# ── Claude mock shape ────────────────────────────────────────────────────────

@dataclass
class _TextBlock:
    type: str
    text: str


@dataclass
class _ClaudeResponse:
    content: list


def _claude_response(text: str) -> _ClaudeResponse:
    return _ClaudeResponse(content=[_TextBlock(type="text", text=text)])


def _mock_claude_client(responses: list):
    """Mock anthropic client: messages.create returns the next queued
    response (or raises if it's an Exception)."""
    client = MagicMock()
    iterator = iter(responses)

    def _create(**kwargs):
        nxt = next(iterator)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    client.messages.create.side_effect = _create
    return client


# ── OpenAI mock shape ────────────────────────────────────────────────────────

@dataclass
class _OpenAIMessage:
    content: str


@dataclass
class _OpenAIChoice:
    message: _OpenAIMessage


@dataclass
class _OpenAIResponse:
    choices: list


def _openai_response(text: str) -> _OpenAIResponse:
    return _OpenAIResponse(choices=[_OpenAIChoice(message=_OpenAIMessage(content=text))])


def _mock_openai_client(responses: list):
    """Mock openai client: chat.completions.create returns the next queued
    response (or raises if it's an Exception)."""
    client = MagicMock()
    iterator = iter(responses)

    def _create(**kwargs):
        nxt = next(iterator)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    client.chat.completions.create.side_effect = _create
    return client


# ── Backward-compatible aliases so old tests keep passing ────────────────────

_mock_response = _claude_response
_mock_client = _mock_claude_client


# ── detect_refusal ───────────────────────────────────────────────────────────

class TestDetectRefusal:
    @pytest.mark.parametrize("text", [
        "I cannot process this image.",
        "I can't extract values from this document.",
        "I am unable to assist with that request.",
        "I apologize, but I cannot help with this.",
        "As an AI, I cannot process medical records.",
        "I'm not able to process this image.",
        "This appears to contain personal information that I should not extract.",
    ])
    def test_positive_refusals(self, text):
        assert detect_refusal(text) is True

    @pytest.mark.parametrize("text", [
        '[{"test_name": "Hemoglobin", "value": "12.5"}]',
        '{"results": []}',
        'The following values were extracted:\n[{"test_name": "Hgb"}]',
        "",
    ])
    def test_negative_not_refusals(self, text):
        assert detect_refusal(text) is False

    def test_refusal_only_matched_in_head(self):
        """A phrase matching late in the text (past 500 chars) shouldn't trip
        the detector — that prevents false positives when a legitimate data
        row contains an innocuous 'as an AI' substring."""
        padding = "Valid extraction output. " * 30  # >500 chars of real output
        text = padding + "\nNote: as an AI context..."
        assert detect_refusal(text) is False


# ── _parse_response_json ─────────────────────────────────────────────────────

class TestParseResponseJson:
    def test_clean_json_array(self):
        result = _parse_response_json('[{"a": 1}, {"b": 2}]')
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_array(self):
        assert _parse_response_json("[]") == []

    def test_whitespace_only(self):
        assert _parse_response_json("   \n  ") == []

    def test_code_fenced_json(self):
        wrapped = "```json\n[{\"a\": 1}]\n```"
        assert _parse_response_json(wrapped) == [{"a": 1}]

    def test_code_fenced_no_language(self):
        wrapped = "```\n[{\"a\": 1}]\n```"
        assert _parse_response_json(wrapped) == [{"a": 1}]

    def test_prose_wrapped_json(self):
        text = 'Here is the extracted data:\n[{"a": 1}]\nLet me know if you need more.'
        assert _parse_response_json(text) == [{"a": 1}]

    def test_malformed_raises(self):
        with pytest.raises(ParseError):
            _parse_response_json("definitely not json")

    def test_non_array_top_level_raises(self):
        """Object at top level is NOT a valid response per the prompt."""
        with pytest.raises(ParseError):
            _parse_response_json('{"not": "an array"}')


# ── _coerce_row ──────────────────────────────────────────────────────────────

class TestCoerceRow:
    def test_full_row_preserved(self):
        row = {
            "test_name": "Hemoglobin",
            "value": "12.5",
            "unit": "g/dL",
            "reference_min": 12.0,
            "reference_max": 15.5,
            "measured_date": "2026-03-15",
            "page": 0,
            "confidence": 0.95,
            "loinc_code": "718-7",
            "loinc_name": "Hemoglobin [Mass/volume] in Blood",
            "loinc_default_unit": "g/dL",
        }
        result = _coerce_row(row, batch_index=0)
        assert result["test_name"] == "Hemoglobin"
        assert result["confidence"] == 0.95
        assert result["loinc_code"] == "718-7"
        assert result["batch_index"] == 0

    def test_numeric_value_coerced_to_string(self):
        """Prompt says string, but LLM sometimes returns a number anyway."""
        row = {"test_name": "Hgb", "value": 12.5, "unit": "g/dL"}
        result = _coerce_row(row, batch_index=0)
        assert result["value"] == "12.5"

    def test_confidence_clamped_to_unit_interval(self):
        row = {"test_name": "Hgb", "confidence": 1.5}
        assert _coerce_row(row, batch_index=0)["confidence"] == 1.0
        row2 = {"test_name": "Hgb", "confidence": -0.3}
        assert _coerce_row(row2, batch_index=0)["confidence"] == 0.0

    def test_missing_fields_get_defaults(self):
        result = _coerce_row({"test_name": "Hgb"}, batch_index=0)
        assert result["value"] is None
        assert result["unit"] == ""
        assert result["reference_min"] is None
        assert result["loinc_code"] == ""

    def test_bad_numeric_reference_becomes_none(self):
        row = {"test_name": "Hgb", "reference_min": "not a number"}
        assert _coerce_row(row, batch_index=0)["reference_min"] is None


# ── extract_batch ────────────────────────────────────────────────────────────

def _page_batch(text_in_image: bytes = b"\xff\xd8\xff\xe0fake_jpeg") -> PageBatch:
    return PageBatch(
        batch_index=0,
        pages=[PageImage(page_index=0, image_bytes=text_in_image)],
    )


class TestExtractBatch:
    def test_happy_path_returns_parsed_rows(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"

        client = _mock_client([
            _mock_response('[{"test_name":"Hemoglobin","value":"12.5","unit":"g/dL","confidence":0.95,"loinc_code":"718-7"}]'),
        ])

        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            results = extract_batch(_page_batch(), total_batches=1)

        assert len(results) == 1
        assert results[0]["test_name"] == "Hemoglobin"
        assert results[0]["loinc_code"] == "718-7"
        assert results[0]["batch_index"] == 0

    def test_refusal_raises(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([_mock_response("I apologize, but I cannot process this image.")])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            with pytest.raises(RefusalError):
                extract_batch(_page_batch(), total_batches=1)

    def test_malformed_response_raises_parse_error(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([_mock_response("sorry no json here")])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            with pytest.raises(ParseError):
                extract_batch(_page_batch(), total_batches=1)

    def test_missing_api_key_raises(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        with pytest.raises(Exception) as exc:
            extract_batch(_page_batch(), total_batches=1)
        assert "ANTHROPIC_API_KEY" in str(exc.value)

    def test_paged_batch_system_prompt_includes_context(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([_mock_response("[]")])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            extract_batch(_page_batch(), total_batches=3)
        call = client.messages.create.call_args
        system = call.kwargs["system"]
        assert "batch 1 of 3" in system


# ── extract (top-level) with retry ───────────────────────────────────────────

class TestExtractTopLevel:
    def test_parse_error_retries_once_then_succeeds(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([
            _mock_response("not json first time"),           # first call: ParseError
            _mock_response('[{"test_name":"Hgb","value":"12.5"}]'),  # retry succeeds
        ])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            results = extract([PageImage(page_index=0, image_bytes=b"x")])
        assert len(results) == 1

    def test_parse_error_retries_once_then_raises(self, settings):
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([
            _mock_response("bad"),
            _mock_response("still bad"),
        ])
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            with pytest.raises(ParseError):
                extract([PageImage(page_index=0, image_bytes=b"x")])

    def test_paged_extraction_merges_batches(self, settings):
        """12 pages → 2 batches. Each returns one unique row; merge returns both."""
        settings.ANTHROPIC_API_KEY = "sk-fake"
        client = _mock_client([
            _mock_response('[{"test_name":"Hgb","value":"12.5","unit":"g/dL"}]'),
            _mock_response('[{"test_name":"WBC","value":"7.2","unit":"10^3/uL"}]'),
        ])
        pages = [PageImage(page_index=i, image_bytes=b"x") for i in range(12)]
        with patch("apps.labs.parsers.llm_parser._get_anthropic_client", return_value=client):
            results = extract(pages)
        assert {r["test_name"] for r in results} == {"Hgb", "WBC"}


# ── merge_results dedup ──────────────────────────────────────────────────────

def _row(test_name: str, value: str, unit: str = "", date: str = "2026-03-15",
         confidence: float = 0.9, batch_index: int = 0):
    return {
        "test_name": test_name,
        "value": value,
        "unit": unit,
        "reference_min": None,
        "reference_max": None,
        "measured_date": date,
        "page": 0,
        "confidence": confidence,
        "loinc_code": "",
        "loinc_name": "",
        "loinc_default_unit": "",
        "batch_index": batch_index,
    }


class TestMergeResults:
    def test_empty_input(self):
        assert merge_results([]) == []

    def test_deduplicates_identical_rows(self):
        r1 = _row("Hgb", "12.5", "g/dL", confidence=0.95, batch_index=0)
        r2 = _row("Hgb", "12.5", "g/dL", confidence=0.90, batch_index=1)
        result = merge_results([r1, r2])
        assert len(result) == 1
        # Higher confidence row wins
        assert result[0]["confidence"] == 0.95

    def test_keeps_earlier_batch_on_tie(self):
        r1 = _row("Hgb", "12.5", "g/dL", confidence=0.9, batch_index=0)
        r2 = _row("Hgb", "12.5", "g/dL", confidence=0.9, batch_index=1)
        result = merge_results([r1, r2])
        assert len(result) == 1
        assert result[0]["batch_index"] == 0

    def test_preserves_distinct_rows(self):
        r1 = _row("Hgb", "12.5", "g/dL")
        r2 = _row("WBC", "7.2", "10^3/uL")
        result = merge_results([r1, r2])
        assert len(result) == 2

    def test_name_normalization_merges_case_variants(self):
        """'Hemoglobin' and 'HEMOGLOBIN' normalize identically → merge."""
        r1 = _row("Hemoglobin", "12.5", "g/dL", confidence=0.95, batch_index=0)
        r2 = _row("HEMOGLOBIN", "12.5", "g/dL", confidence=0.80, batch_index=1)
        result = merge_results([r1, r2])
        assert len(result) == 1

    def test_different_dates_not_merged(self):
        r1 = _row("Hgb", "12.5", "g/dL", date="2026-03-15")
        r2 = _row("Hgb", "12.5", "g/dL", date="2026-04-15")
        result = merge_results([r1, r2])
        assert len(result) == 2


# ── _resolve_provider ────────────────────────────────────────────────────────

class TestResolveProvider:
    def test_claude_default(self, settings):
        settings.LAB_LLM_PROVIDER = "claude"
        assert _resolve_provider() == "claude"

    def test_openai(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        assert _resolve_provider() == "openai"

    def test_unknown_value_falls_back_to_claude(self, settings):
        settings.LAB_LLM_PROVIDER = "gemini"  # not supported
        assert _resolve_provider() == "claude"

    def test_empty_falls_back_to_claude(self, settings):
        settings.LAB_LLM_PROVIDER = ""
        assert _resolve_provider() == "claude"

    def test_case_insensitive(self, settings):
        settings.LAB_LLM_PROVIDER = "OpenAI"
        assert _resolve_provider() == "openai"


# ── OpenAI provider path ─────────────────────────────────────────────────────

class TestOpenAIProvider:
    def test_happy_path_returns_parsed_rows(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"

        client = _mock_openai_client([
            _openai_response(
                '[{"test_name":"Hemoglobin","value":"12.5","unit":"g/dL","confidence":0.9,"loinc_code":"718-7"}]'
            ),
        ])

        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            results = extract_batch(_page_batch(), total_batches=1)

        assert len(results) == 1
        assert results[0]["test_name"] == "Hemoglobin"
        assert results[0]["loinc_code"] == "718-7"

    def test_refusal_raises(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"

        client = _mock_openai_client([
            _openai_response("I'm sorry, but I cannot process this image."),
        ])
        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            with pytest.raises(RefusalError) as exc:
                extract_batch(_page_batch(), total_batches=1)
        assert "openai" in str(exc.value).lower()

    def test_parse_error_on_malformed_response(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"

        client = _mock_openai_client([_openai_response("not valid json")])
        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            with pytest.raises(ParseError):
                extract_batch(_page_batch(), total_batches=1)

    def test_missing_api_key_raises(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = ""
        with pytest.raises(ExtractionError) as exc:
            extract_batch(_page_batch(), total_batches=1)
        assert "OPENAI_API_KEY" in str(exc.value)

    def test_empty_choices_returns_empty_list(self, settings):
        """Degenerate OpenAI response with empty choices → treated as empty
        extraction (not a crash, not a refusal)."""
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"
        client = MagicMock()
        client.chat.completions.create.return_value = _OpenAIResponse(choices=[])
        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            results = extract_batch(_page_batch(), total_batches=1)
        assert results == []

    def test_paged_batch_context_in_system_prompt(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"
        client = _mock_openai_client([_openai_response("[]")])
        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            extract_batch(_page_batch(), total_batches=3)
        call = client.chat.completions.create.call_args
        # System prompt is the first message
        messages = call.kwargs["messages"]
        system_msg = next(m for m in messages if m["role"] == "system")
        assert "batch 1 of 3" in system_msg["content"]

    def test_uses_configured_model(self, settings):
        settings.LAB_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "sk-fake"
        settings.LAB_OPENAI_MODEL = "gpt-4o-mini"
        client = _mock_openai_client([_openai_response("[]")])
        with patch("apps.labs.parsers.llm_parser._get_openai_client", return_value=client):
            extract_batch(_page_batch(), total_batches=1)
        call = client.chat.completions.create.call_args
        assert call.kwargs["model"] == "gpt-4o-mini"


# ── Provider parity ──────────────────────────────────────────────────────────

class TestProviderParity:
    """Both providers should behave identically on the shared pieces: refusal
    detection, JSON recovery, paged-merge orchestration. Parametrize over
    provider to keep the cover surface symmetric."""

    @pytest.mark.parametrize("provider", ["claude", "openai"])
    def test_paged_extraction_runs_one_call_per_batch(self, settings, provider):
        settings.LAB_LLM_PROVIDER = provider
        settings.ANTHROPIC_API_KEY = "sk-fake"
        settings.OPENAI_API_KEY = "sk-fake"

        pages = [PageImage(page_index=i, image_bytes=b"x") for i in range(12)]

        if provider == "claude":
            client = _mock_claude_client([
                _claude_response('[{"test_name":"Hgb","value":"12.5"}]'),
                _claude_response('[{"test_name":"WBC","value":"7.2"}]'),
            ])
            patch_path = "apps.labs.parsers.llm_parser._get_anthropic_client"
            call_count = lambda c: c.messages.create.call_count
        else:
            client = _mock_openai_client([
                _openai_response('[{"test_name":"Hgb","value":"12.5"}]'),
                _openai_response('[{"test_name":"WBC","value":"7.2"}]'),
            ])
            patch_path = "apps.labs.parsers.llm_parser._get_openai_client"
            call_count = lambda c: c.chat.completions.create.call_count

        with patch(patch_path, return_value=client):
            results = extract(pages)

        assert {r["test_name"] for r in results} == {"Hgb", "WBC"}
        assert call_count(client) == 2
