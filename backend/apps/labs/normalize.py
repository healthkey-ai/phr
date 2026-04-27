"""
Shared normalization functions for LOINC alias curation and runtime matching.

Used by both the offline pipeline (management commands) and the Tier-1
matcher, so this module must NOT import Django models at module level.
"""
import re
import unicodedata

_LOINC_RE = re.compile(r"(\d{1,5}-\d)")
_TRAILING_PARENS = re.compile(r"\s*\([^)]*\)\s*$")
_LEADING_PARENS = re.compile(r"^\s*\([^)]*\)\s*")
_BOUNDARY_PUNCT = re.compile(r"^[^\w\s]+|[^\w\s]+$")


def normalize(raw: str) -> str:
    """Produce the lookup key used by both the fixture builder and Tier-1 index.

    Pipeline:
      1. Unicode NFKC
      2. Lowercase
      3. Strip trailing parenthesized content
      4. Strip leading parenthesized content
      5. Collapse whitespace
      6. Strip boundary punctuation (keep + - / . inside tokens)
      7. Clamp to 100 chars
    """
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", str(raw))
    s = s.lower()
    s = _TRAILING_PARENS.sub("", s)
    s = _LEADING_PARENS.sub("", s)
    s = " ".join(s.split())
    s = _BOUNDARY_PUNCT.sub("", s)
    s = s.strip()
    return s[:100]


def normalize_loinc(raw: str | None) -> str:
    """Canonical NNNNN-N format or empty string."""
    if not raw:
        return ""
    s = raw.replace("–", "-").replace("—", "-").strip()
    m = _LOINC_RE.search(s)
    return m.group(1) if m else ""


def normalize_name(raw: str | None) -> str:
    """NFKD + casefold + strip non-alnum. Used for LabTestEntry.name_normalized."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw)).casefold()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())
