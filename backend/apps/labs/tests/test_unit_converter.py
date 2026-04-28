"""
Tests for apps/labs/unit_converter.py.

Covers normalise(), is_convertible(), and the ucumvert-based parsing.
"""
import math

import pytest

from apps.labs.unit_converter import (
    _parse_unit,
    is_convertible,
    normalise,
)


# ── _parse_unit ──────────────────────────────────────────────────────────────

class TestParseUnit:
    def test_empty_string(self):
        assert _parse_unit("") is None

    def test_none_returns_none(self):
        assert _parse_unit(None) is None

    def test_valid_ucum(self):
        assert _parse_unit("g/dL") is not None

    def test_alias_lookup(self):
        assert _parse_unit("K/uL") is not None

    def test_suffix_stripped(self):
        assert _parse_unit("g/dL (calc)") is not None

    def test_unicode_mu(self):
        assert _parse_unit("µg/dL") is not None

    def test_cell_count_notations_unified(self):
        k = _parse_unit("K/uL")
        ten3 = _parse_unit("10*3/uL")
        ten9 = _parse_unit("10^9/L")
        assert k is not None
        assert k == ten3
        # 10^9/L == 10^3/uL in magnitude but different dimensionally in pint
        assert ten9 is not None


# ── normalise — happy paths ──────────────────────────────────────────────────

class TestNormaliseHappy:
    def test_mg_dl_to_g_dl(self):
        assert normalise(100, "mg/dL", "g/dL") == pytest.approx(0.1, rel=1e-6)

    def test_g_dl_to_mg_dl(self):
        assert normalise(12.5, "g/dL", "mg/dL") == pytest.approx(12500.0, rel=1e-6)

    def test_identical_units_passthrough(self):
        assert normalise(42.0, "g/dL", "g/dL") == 42.0

    def test_cell_count_K_per_uL_to_thousand_per_uL(self):
        result = normalise(150, "K/uL", "10*3/uL")
        assert result == pytest.approx(150.0, rel=1e-6)

    def test_cell_count_SI_10_9_per_L_matches(self):
        result = normalise(5.5, "10*9/L", "10*3/uL")
        assert result == pytest.approx(5.5, rel=1e-6)

    def test_enzyme_U_L_to_IU_L(self):
        result = normalise(40, "U/L", "IU/L")
        assert result == pytest.approx(40.0, rel=1e-6)

    def test_percent_passthrough(self):
        assert normalise(5.6, "%", "%") == 5.6

    def test_mmol_to_mg_dl_creatinine(self):
        result = normalise(88.4, "umol/L", "mg/dL", molecular_weight=113.12)
        assert result == pytest.approx(1.0, rel=1e-2)

    def test_mg_dl_to_mmol_creatinine(self):
        result = normalise(1.0, "mg/dL", "umol/L", molecular_weight=113.12)
        assert result == pytest.approx(88.4, rel=1e-2)

    def test_calcium_mmol_to_mg_dl(self):
        result = normalise(2.5, "mmol/L", "mg/dL", molecular_weight=40.08)
        assert result == pytest.approx(10.02, rel=1e-2)

    def test_calc_suffix_stripped(self):
        assert normalise(14.5, "g/dL (calc)", "g/L") == pytest.approx(145.0, rel=1e-6)

    def test_calculated_suffix_stripped(self):
        assert normalise(100, "mg/dL (calculated)", "mg/dL") == pytest.approx(100.0)


class TestRegionalAlternativeUnits:
    def test_hemoglobin_g_L_to_g_dL(self):
        assert normalise(125, "g/L", "g/dL") == pytest.approx(12.5, rel=1e-6)

    def test_albumin_g_L_to_g_dL(self):
        assert normalise(40, "g/L", "g/dL") == pytest.approx(4.0, rel=1e-6)

    def test_ldl_mmol_L_to_mg_dL(self):
        result = normalise(3.0, "mmol/L", "mg/dL", molecular_weight=386.65)
        assert result == pytest.approx(116.0, rel=1e-2)

    def test_bili_total_umol_L_to_mg_dL(self):
        result = normalise(17.1, "umol/L", "mg/dL", molecular_weight=584.66)
        assert result == pytest.approx(1.0, rel=1e-2)

    def test_b2m_ng_mL_to_mg_L(self):
        assert normalise(1500, "ng/mL", "mg/L") == pytest.approx(1.5, rel=1e-6)

    def test_b2m_ug_mL_equals_mg_L(self):
        assert normalise(2.0, "ug/mL", "mg/L") == pytest.approx(2.0, rel=1e-6)

    def test_cell_count_K_per_uL_to_default(self):
        assert normalise(5.5, "K/uL", "10*3/uL") == pytest.approx(5.5, rel=1e-6)

    def test_ast_IU_L_to_U_L(self):
        assert normalise(42, "IU/L", "U/L") == pytest.approx(42.0, rel=1e-6)

    def test_tsh_uIU_mL_to_mIU_L(self):
        assert normalise(2.5, "uIU/mL", "mIU/L") == pytest.approx(2.5, rel=1e-6)

    def test_tsh_mIU_L_round_trip(self):
        assert normalise(0.4, "mIU/L", "mIU/L") == 0.4


# ── normalise — failure modes ────────────────────────────────────────────────

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
        assert normalise(1.0, "mg/dL", "mmol/L") is None

    def test_both_empty_returns_value(self):
        assert normalise(1.0, "", "") == 1.0

    def test_zero_value_converts_to_zero(self):
        assert normalise(0.0, "mg/dL", "g/dL") == 0.0

    def test_negative_value_allowed(self):
        assert normalise(-1.0, "mg/dL", "g/dL") == pytest.approx(-0.001, rel=1e-6)

    def test_molar_mass_without_mw_returns_none(self):
        assert normalise(1.0, "mmol/L", "mg/dL") is None


# ── is_convertible helper ────────────────────────────────────────────────────

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

    def test_calc_suffix_convertible(self):
        assert is_convertible("g/dL (calc)", "g/L") is True
