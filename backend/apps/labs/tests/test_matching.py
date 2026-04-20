"""
Tests for apps.labs.matching — Phase 2c identity resolution.

Covers:
  - normalize_loinc (format variants, garbage input)
  - normalize_name (Unicode folding, punctuation, casefold)
  - resolve_test_identity:
      - validated LOINC hits an existing curated row
      - validated LOINC auto-creates a row (fixture-hydrated)
      - LOINC hallucinated (not in fixture) → name fallback
      - name fallback reuses existing no-LOINC row
      - name fallback creates new no-LOINC row
      - empty LOINC + empty name → still produces a row
      - abbreviation slug collision appends -N
  - LOINC_COMMON fixture loads successfully
"""
import pytest
from django.core.management import call_command

from apps.labs.matching import (
    LOINC_COMMON,
    normalize_loinc,
    normalize_name,
    resolve_test_identity,
)
from apps.labs.models import LabTestType, MatchMethod


# ── Fixture loader ────────────────────────────────────────────────────────────

class TestLoincFixture:
    def test_fixture_loaded(self):
        assert len(LOINC_COMMON) > 100, "Fixture should have 100+ entries"
        assert "718-7" in LOINC_COMMON
        assert LOINC_COMMON["718-7"]["loinc_short_name"] == "Hemoglobin"
        assert LOINC_COMMON["718-7"]["loinc_default_unit"] == "g/dL"
        assert LOINC_COMMON["718-7"]["value_type"] == "numeric"

    def test_qualitative_entries_present(self):
        """HIV antibody should be a qualitative entry with empty default_unit."""
        assert "75622-1" in LOINC_COMMON
        entry = LOINC_COMMON["75622-1"]
        assert entry["value_type"] == "qualitative"
        assert entry["loinc_default_unit"] == ""

    def test_ratio_entries_present(self):
        """INR ships as a ratio with no unit."""
        assert "6301-6" in LOINC_COMMON
        entry = LOINC_COMMON["6301-6"]
        assert entry["value_type"] == "ratio"


# ── normalize_loinc ───────────────────────────────────────────────────────────

class TestNormalizeLoinc:
    def test_canonical_format_passthrough(self):
        assert normalize_loinc("718-7") == "718-7"
        assert normalize_loinc("62238-1") == "62238-1"

    def test_strips_prefix(self):
        assert normalize_loinc("LOINC:718-7") == "718-7"
        assert normalize_loinc("LOINC 718-7") == "718-7"

    def test_handles_endash(self):
        # U+2013 en-dash → ASCII hyphen
        assert normalize_loinc("718\u20137") == "718-7"

    def test_strips_whitespace(self):
        assert normalize_loinc("  718-7  ") == "718-7"
        assert normalize_loinc("\t718-7\n") == "718-7"

    def test_empty_returns_empty(self):
        assert normalize_loinc("") == ""
        assert normalize_loinc(None) == ""

    def test_missing_checksum_returns_empty(self):
        """'718' alone (no checksum dash) is NOT a valid LOINC — reject."""
        assert normalize_loinc("718") == ""

    def test_pure_garbage_returns_empty(self):
        assert normalize_loinc("not a loinc") == ""
        assert normalize_loinc("XYZ-A") == ""


# ── normalize_name ────────────────────────────────────────────────────────────

class TestNormalizeName:
    def test_case_folded(self):
        assert normalize_name("Hemoglobin") == "hemoglobin"
        assert normalize_name("HGB") == "hgb"

    def test_punctuation_stripped(self):
        assert normalize_name("CA 15-3") == "ca 15 3"
        assert normalize_name("Kappa/Lambda FLC ratio") == "kappa lambda flc ratio"

    def test_collapses_whitespace(self):
        assert normalize_name("Hemoglobin    A1c") == "hemoglobin a1c"

    def test_unicode_micro_folds(self):
        """U+00B5 µ-sign should decompose via NFKD."""
        # µ (U+00B5) → μ (U+03BC). We don't ASCII-strip — just ensure the
        # normalized form is deterministic for matching.
        result = normalize_name("µg/dL")
        # Both inputs should produce the same normalized string
        assert normalize_name("μg/dL") == result

    def test_empty_input(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""


# ── resolve_test_identity — Tier 0a validated LOINC ──────────────────────────

@pytest.fixture
def catalog(db):
    call_command("loaddata", "lab_catalog.json", app_label="labs", verbosity=0)


@pytest.mark.django_db
class TestResolveValidatedLoinc:
    def test_matches_existing_curated_row(self, catalog):
        """Hemoglobin's LOINC (718-7) already has a LabTestType in lab_catalog.json.
        resolve_test_identity should return THAT row, not create a new one."""
        before = LabTestType.objects.count()
        tt, method = resolve_test_identity("Hemoglobin", "718-7", "g/dL")
        assert tt.abbreviation == "hgb"
        assert tt.loinc_code == "718-7"
        assert method == MatchMethod.LOINC
        assert LabTestType.objects.count() == before  # no new row

    def test_loinc_with_junk_prefix_normalises(self, catalog):
        tt, method = resolve_test_identity("Hemoglobin", "LOINC:718-7", "g/dL")
        assert tt.loinc_code == "718-7"
        assert method == MatchMethod.LOINC

    def test_loinc_with_endash_normalises(self, catalog):
        tt, method = resolve_test_identity("Hemoglobin", "718\u20137", "g/dL")
        assert tt.loinc_code == "718-7"
        assert method == MatchMethod.LOINC

    def test_auto_creates_for_validated_but_uncurated_loinc(self, catalog):
        """Ferritin (2276-4) is in loinc_common.json but NOT preloaded as a
        LabTestType. First sight should auto-create a row hydrated from the
        fixture."""
        assert not LabTestType.objects.filter(loinc_code="2276-4").exists()

        tt, method = resolve_test_identity("Ferritin", "2276-4", "ng/mL")

        assert method == MatchMethod.LOINC
        assert tt.loinc_code == "2276-4"
        assert tt.name == "Ferritin"  # from fixture short_name
        assert tt.default_unit == "ng/mL"
        assert tt.value_type == "numeric"
        # Second call returns the same row (idempotent)
        tt2, _ = resolve_test_identity("Ferritin", "2276-4", "ng/mL")
        assert tt2.pk == tt.pk

    def test_hallucinated_loinc_matches_existing_by_name(self, catalog):
        """A LOINC not in the fixture falls back to name matching. If the
        extracted name matches an existing row (via name_normalized), link
        to it — even though that row's loinc_code is different."""
        tt, method = resolve_test_identity("Hemoglobin", "99999-9", "g/dL")
        assert method == MatchMethod.NAME_FALLBACK
        # Matched the existing Hemoglobin row (preloaded with LOINC 718-7)
        assert tt.abbreviation == "hgb"
        assert tt.loinc_code == "718-7"


# ── resolve_test_identity — name fallback (no LOINC) ─────────────────────────

@pytest.mark.django_db
class TestResolveNameFallback:
    def test_empty_loinc_reuses_existing_row(self, catalog):
        tt, method = resolve_test_identity("Hemoglobin", "", "g/dL")
        assert method == MatchMethod.NAME_FALLBACK
        assert tt.abbreviation == "hgb"

    def test_none_loinc_reuses_existing_row(self, catalog):
        tt, method = resolve_test_identity("Hemoglobin", None, "g/dL")
        assert method == MatchMethod.NAME_FALLBACK
        assert tt.abbreviation == "hgb"

    def test_creates_row_for_novel_name(self, catalog):
        """A test name that doesn't match any existing row → create a
        no-LOINC LabTestType stub."""
        before = LabTestType.objects.count()
        tt, method = resolve_test_identity("MysteryMetabolite", None, "units")
        assert method == MatchMethod.NAME_FALLBACK
        assert tt.loinc_code == ""
        assert tt.name == "MysteryMetabolite"
        assert tt.name_normalized == "mysterymetabolite"
        assert tt.abbreviation == "mysterymetabolite"
        assert tt.default_unit == "units"
        assert LabTestType.objects.count() == before + 1

    def test_idempotent_creation_for_novel_name(self, catalog):
        """Calling twice with the same novel name should return the SAME row."""
        tt1, _ = resolve_test_identity("ObscureTest", None, "mg/dL")
        tt2, _ = resolve_test_identity("ObscureTest", None, "mg/dL")
        assert tt1.pk == tt2.pk

    def test_name_variations_match_same_normalized_row(self, catalog):
        """'Obscure Test' and 'OBSCURE   TEST' normalize identically → same row."""
        tt1, _ = resolve_test_identity("Obscure Test", None, "mg/dL")
        tt2, _ = resolve_test_identity("OBSCURE   TEST", None, "mg/dL")
        assert tt1.pk == tt2.pk

    def test_empty_name_and_loinc_still_creates_row(self, catalog):
        """Pathological input — both empty — should still produce SOMETHING
        rather than crash. Parks it under the 'unknown test' bucket."""
        tt, method = resolve_test_identity("", None, "")
        assert method == MatchMethod.NAME_FALLBACK
        assert tt is not None
        assert tt.name_normalized == "unknown test"


# ── Abbreviation slug collision ──────────────────────────────────────────────

@pytest.mark.django_db
class TestSlugCollision:
    def test_auto_created_slug_appends_suffix_on_collision(self, catalog):
        """If auto-creating a row whose slug collides with an existing row,
        append -2. `hgb` already exists from the catalog, so creating a
        no-LOINC row named 'HGB' should produce a slug like `hgb-2`."""
        # Preload: "hgb" is already taken
        assert LabTestType.objects.filter(abbreviation="hgb").exists()

        # Create a NEW row via resolve_test_identity with a name that slugs to "hgb"
        # but different normalized name so it doesn't merge.
        # Tricky: "HGB" normalizes to "hgb", which matches the existing row's
        # name_normalized. So it'll merge, not collide. To exercise slug
        # collision, we need a name that slugs to an existing abbreviation
        # but normalizes to something distinct.
        #
        # Example: existing abbreviation "hgb", new name "H.G.B.". Slug of
        # "H.G.B." = "h-g-b" → normalized -> "h g b" -> still hits slug "h-g-b"?
        # Let's use a name that slugs identically to an existing row but normalizes
        # differently. "Creatinine!!" slugs to "creatinine", normalizes to
        # "creatinine" — still merges. Tricky.
        #
        # Simpler: directly call _slug_with_collision_suffix.
        from apps.labs.matching import _slug_with_collision_suffix
        candidate = _slug_with_collision_suffix("hgb")
        assert candidate == "hgb-2"
