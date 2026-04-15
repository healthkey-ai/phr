"""
Tests for apps/labs/unit_converter.py.

Covers every branch in normalise() and _canonicalise() per the test review
coverage diagram in docs/patient-app-lab-upload-design.md §3.2.
"""
import math

import pytest

from apps.labs.unit_converter import (
    _canonicalise,
    is_convertible,
    normalise,
)


# ── _canonicalise ─────────────────────────────────────────────────────────────

class TestCanonicalise:
    def test_empty_string(self):
        assert _canonicalise("") == ""

    def test_none_returns_empty(self):
        assert _canonicalise(None) == ""

    def test_whitespace_collapsed(self):
        assert _canonicalise("  mg/dL  ") == "milligram / deciliter"

    def test_lowercased(self):
        assert _canonicalise("MG/DL") == "milligram / deciliter"

    def test_unicode_mu_folds_to_u(self):
        # µ (U+00B5) decomposes to u via NFKD
        assert _canonicalise("µg/dL") == _canonicalise("ug/dL")

    def test_unicode_greek_mu_folds_to_u(self):
        # μ (U+03BC, Greek small letter mu) is not strictly NFKD-decomposed
        # but our alias map handles it explicitly
        result = _canonicalise("μmol/L")
        assert "micromole" in result

    def test_mcg_alias(self):
        assert _canonicalise("mcg") == "microgram"

    def test_cell_count_notations_unified(self):
        # All three notations should canonicalise to the same string
        assert _canonicalise("K/uL") == "thousand_per_uL"
        assert _canonicalise("10^3/uL") == "thousand_per_uL"
        assert _canonicalise("10^9/L") == "thousand_per_uL"


# ── normalise — happy paths ───────────────────────────────────────────────────

class TestNormaliseHappy:
    def test_mg_dl_to_g_dl(self):
        # 100 mg/dL = 0.1 g/dL
        assert normalise(100, "mg/dL", "g/dL") == pytest.approx(0.1, rel=1e-6)

    def test_g_dl_to_mg_dl(self):
        # 12.5 g = 12_500 mg; per-dL same
        assert normalise(12.5, "g/dL", "mg/dL") == pytest.approx(12500.0, rel=1e-6)

    def test_identical_units_passthrough(self):
        assert normalise(42.0, "g/dL", "g/dL") == 42.0

    def test_cell_count_K_per_uL_to_thousand_per_uL(self):
        # Same magnitude, different notation
        result = normalise(150, "K/uL", "10^3/uL")
        assert result == pytest.approx(150.0, rel=1e-6)

    def test_cell_count_SI_10_9_per_L_matches(self):
        # 10^9/L is numerically identical to 10^3/µL
        result = normalise(5.5, "10^9/L", "10^3/uL")
        assert result == pytest.approx(5.5, rel=1e-6)

    def test_enzyme_U_L_to_IU_L(self):
        # We define U and IU as aliases
        result = normalise(40, "U/L", "IU/L")
        assert result == pytest.approx(40.0, rel=1e-6)

    def test_percent_passthrough(self):
        assert normalise(5.6, "%", "%") == 5.6

    def test_mmol_to_mg_dl_creatinine(self):
        # Creatinine MW = 113.12
        # 88.4 µmol/L × 113.12 g/mol = 10000 ng/mL = 1 mg/dL
        result = normalise(88.4, "umol/L", "mg/dL", molecular_weight=113.12)
        assert result == pytest.approx(1.0, rel=1e-2)

    def test_mg_dl_to_mmol_creatinine(self):
        result = normalise(1.0, "mg/dL", "umol/L", molecular_weight=113.12)
        assert result == pytest.approx(88.4, rel=1e-2)

    def test_calcium_mmol_to_mg_dl(self):
        # Ca MW = 40.08
        # 2.5 mmol/L × 40.08 = 100.2 mg/L = 10.02 mg/dL
        result = normalise(2.5, "mmol/L", "mg/dL", molecular_weight=40.08)
        assert result == pytest.approx(10.02, rel=1e-2)


class TestRegionalAlternativeUnits:
    """Round-trip tests for the UK/EU/US alternative units per test type.
    Mirrors the fixture's `alternative_units` lists."""

    def test_hemoglobin_g_L_to_g_dL(self):
        # UK/EU: 125 g/L → US: 12.5 g/dL
        assert normalise(125, "g/L", "g/dL") == pytest.approx(12.5, rel=1e-6)

    def test_albumin_g_L_to_g_dL(self):
        # 40 g/L → 4.0 g/dL
        assert normalise(40, "g/L", "g/dL") == pytest.approx(4.0, rel=1e-6)

    def test_ldl_mmol_L_to_mg_dL(self):
        # LDL cholesterol MW 386.65
        # 3.0 mmol/L × 386.65 = 1159.95 mg/L = 115.995 mg/dL
        result = normalise(3.0, "mmol/L", "mg/dL", molecular_weight=386.65)
        assert result == pytest.approx(116.0, rel=1e-2)

    def test_bili_total_umol_L_to_mg_dL(self):
        # Bilirubin MW 584.66. 17 µmol/L ≈ 1.0 mg/dL
        result = normalise(17.1, "umol/L", "mg/dL", molecular_weight=584.66)
        assert result == pytest.approx(1.0, rel=1e-2)

    def test_b2m_ng_mL_to_mg_L(self):
        # B2M is reported in both. 1500 ng/mL = 1.5 mg/L
        assert normalise(1500, "ng/mL", "mg/L") == pytest.approx(1.5, rel=1e-6)

    def test_b2m_ug_mL_equals_mg_L(self):
        # 1 ug/mL is numerically identical to 1 mg/L
        assert normalise(2.0, "ug/mL", "mg/L") == pytest.approx(2.0, rel=1e-6)

    def test_cell_count_K_per_uL_to_default(self):
        # Lab reports sometimes use K/uL even when the default is 10^3/uL
        assert normalise(5.5, "K/uL", "10^3/uL") == pytest.approx(5.5, rel=1e-6)

    def test_ast_IU_L_to_U_L(self):
        # IU/L and U/L are aliased enzyme units
        assert normalise(42, "IU/L", "U/L") == pytest.approx(42.0, rel=1e-6)

    def test_tsh_uIU_mL_to_mIU_L(self):
        # Numerically identical — both express thousandth of an IU
        assert normalise(2.5, "uIU/mL", "mIU/L") == pytest.approx(2.5, rel=1e-6)

    def test_tsh_mIU_L_round_trip(self):
        assert normalise(0.4, "mIU/L", "mIU/L") == 0.4


# ── normalise — failure modes ─────────────────────────────────────────────────

class TestNormaliseFailures:
    def test_none_value_returns_none(self):
        assert normalise(None, "mg/dL", "g/dL") is None

    def test_nan_value_returns_none(self):
        assert normalise(float("nan"), "mg/dL", "g/dL") is None

    def test_unknown_from_unit_returns_none(self):
        assert normalise(1.0, "zottaflops/parsec", "mg/dL") is None

    def test_unknown_to_unit_returns_none(self):
        assert normalise(1.0, "mg/dL", "zottaflops/parsec") is None

    def test_dimensionality_mismatch_without_mw_returns_none(self):
        # mg/dL (mass/volume) can't become mmol/L (mole/volume) without MW
        assert normalise(1.0, "mg/dL", "mmol/L") is None

    def test_empty_strings_return_none(self):
        assert normalise(1.0, "", "") is None

    def test_zero_value_converts_to_zero(self):
        assert normalise(0.0, "mg/dL", "g/dL") == 0.0

    def test_negative_value_allowed(self):
        # Labs don't have negative values but the math still works
        assert normalise(-1.0, "mg/dL", "g/dL") == pytest.approx(-0.001, rel=1e-6)

    def test_molar_mass_without_mw_returns_none(self):
        # Needs molecular_weight but none given
        assert normalise(1.0, "mmol/L", "mg/dL") is None


# ── is_convertible helper ─────────────────────────────────────────────────────

class TestIsConvertible:
    def test_same_dimension_yes(self):
        assert is_convertible("mg/dL", "g/dL") is True

    def test_different_dimension_no(self):
        assert is_convertible("mg/dL", "mmol/L") is False

    def test_different_dimension_with_mw_yes(self):
        assert is_convertible("mg/dL", "mmol/L", molecular_weight=113.12) is True

    def test_identical_yes(self):
        assert is_convertible("g/dL", "g/dL") is True

    def test_unknown_unit_no(self):
        assert is_convertible("zottaflops", "g/dL") is False
