"""
Unit normalisation for lab values.

Primary path: ucumvert parses UCUM strings into pint Quantity objects.
Fallback: a curated alias table maps messy lab-report notation to valid
UCUM before parsing.

Molar <-> mass conversions require a molecular weight (g/mol), stored
per-test in LabTestEntry.molecular_weight.

Contract:
    normalise(value, from_unit, to_unit, molecular_weight=None) -> float | None

Returns None (rather than raising) on any failure so the caller can
surface the issue in the review UI.
"""
from __future__ import annotations

import logging
import math
import re
import unicodedata
from functools import lru_cache
from typing import Optional

import pint
from ucumvert import UcumToPintTransformer, get_ucum_parser

logger = logging.getLogger(__name__)

# ── ucumvert setup ──────────────────────────────────────────────────────────

_parser = get_ucum_parser()
_transformer = UcumToPintTransformer()
_ureg = _transformer.ureg

# ── Parenthetical suffix (e.g. "(calc)", "(estimated)") ─────────────────────

_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


# ── Alias map — lab-report string → valid UCUM ─────────────────────────────
# Keys are lowercased + NFKD-folded.  Values MUST be valid UCUM so ucumvert
# can parse them.  Only add entries for strings that aren't already valid UCUM.

UNIT_ALIASES: dict[str, str] = {
    # Cell-count notations (k = thousand, not Kelvin)
    "k/ul": "10*3/uL",
    "k/µl": "10*3/uL",
    "10^3/ul": "10*3/uL",
    "10**3/ul": "10*3/uL",
    "10e3/ul": "10*3/uL",
    "1000/ul": "10*3/uL",
    "thousand/ul": "10*3/uL",
    "x10(3)/ul": "10*3/uL",
    "x10^3/ul": "10*3/uL",
    "10^9/l": "10*9/L",
    "10**9/l": "10*9/L",
    "10^6/ul": "10*6/uL",
    "10**6/ul": "10*6/uL",
    "x10(6)/ul": "10*6/uL",
    "x10^6/ul": "10*6/uL",
    "m/ul": "10*6/uL",
    "million/ul": "10*6/uL",
    "cells/ul": "/uL",
    # Micro-symbol variants (NFKD doesn't always collapse µ→u)
    "mcg": "ug",
    "mcl": "uL",
    "mcmol": "umol",
    # Mass / volume — fix casing for UCUM
    "mg/dl": "mg/dL",
    "g/dl": "g/dL",
    "ng/ml": "ng/mL",
    "ng/dl": "ng/dL",
    "pg/ml": "pg/mL",
    "pg/dl": "pg/dL",
    "mg/l": "mg/L",
    "g/l": "g/L",
    "mmol/l": "mmol/L",
    "umol/l": "umol/L",
    "mcmol/l": "umol/L",
    "nmol/l": "nmol/L",
    "pmol/l": "pmol/L",
    # Enzyme / hormone activity
    # In lab medicine U ≡ IU; ucumvert treats U (enzyme_unit) and [IU]
    # (international_unit) as different dimensions, so we normalise
    # everything to U (enzyme_unit) for consistency.
    "u/l": "U/L",
    "iu/l": "U/L",
    "[iu]/l": "U/L",
    "iu/ml": "U/mL",
    "[iu]/ml": "U/mL",
    "u/ml": "U/mL",
    "miu/l": "mU/L",
    "m[iu]/l": "mU/L",
    "miu/ml": "mU/mL",
    "m[iu]/ml": "mU/mL",
    "uiu/l": "uU/L",
    "u[iu]/l": "uU/L",
    "uiu/ml": "uU/mL",
    "u[iu]/ml": "uU/mL",
    "k[iu]/l": "kU/L",
    # Percent (lab qualifiers like "of total Hgb" are annotations, not dimensions)
    "pct": "%",
    "% of total hgb": "%",
    "% of total": "%",
    # Time
    "sec": "s",
    "ms": "ms",
    # mEq
    "meq/l": "meq/L",
    # eGFR — various notations for BSA-normalised flow
    "ml/min/1.73m2": "mL/min/{1.73_m2}",
    "ml/min/1.73 m2": "mL/min/{1.73_m2}",
    # Ratio / dimensionless — UCUM {ratio} is an annotation, not a parseable unit;
    # falls through ucumvert to pint direct parse as "dimensionless"
    "ratio": "dimensionless",
    "{ratio}": "dimensionless",
    # Per-24h (time-window, not rate — drop denominator for trending)
    "mg/24h": "mg",
}


# ── Internal helpers ────────────────────────────────────────────────────────

def _normalise_key(raw: str) -> str:
    """Lowercase + NFKD-fold a raw unit string for alias lookup."""
    s = unicodedata.normalize("NFKD", raw).casefold().strip()
    s = s.replace("µ", "u").replace("μ", "u")
    return " ".join(s.split())


@lru_cache(maxsize=512)
def _parse_unit(raw: str) -> Optional[pint.Unit]:
    """Parse a unit string to a pint Unit via ucumvert.

    Order: alias-mapped UCUM (wins for ambiguous strings like K/uL)
           → raw UCUM → pint direct parse.
    """
    if not raw or not raw.strip():
        return None

    s = _SUFFIX_RE.sub("", raw).strip()
    if not s:
        return None

    # 1. Alias lookup → UCUM  (checked first so lab-report conventions
    #    like K/uL = thousand/uL beat UCUM's K = Kelvin)
    key = _normalise_key(s)
    alias = UNIT_ALIASES.get(key)
    if alias:
        try:
            return _transformer.transform(_parser.parse(alias)).units
        except Exception:
            pass
        try:
            return _ureg.parse_units(alias)
        except Exception:
            pass

    # 2. Try raw string as UCUM
    try:
        return _transformer.transform(_parser.parse(s)).units
    except Exception:
        pass

    # 3. Last resort — maybe pint can parse it directly
    try:
        return _ureg.parse_units(key)
    except Exception:
        pass

    return None


# ── Public API ──────────────────────────────────────────────────────────────

def normalise(
    value: float,
    from_unit: str,
    to_unit: str,
    molecular_weight: Optional[float] = None,
) -> Optional[float]:
    """Convert *value* from *from_unit* to *to_unit*.

    Returns the converted float, or None on any failure.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None

    src = _parse_unit(from_unit)
    dst = _parse_unit(to_unit)

    if src is None and dst is None:
        return float(value) if (from_unit or "") == (to_unit or "") else None
    if src is None or dst is None:
        return None

    if src == dst:
        return float(value)

    try:
        return float(_ureg.Quantity(float(value), src).to(dst).magnitude)
    except pint.DimensionalityError:
        if molecular_weight is not None and molecular_weight > 0:
            return _molar_mass_convert(value, src, dst, molecular_weight)
    except (pint.UndefinedUnitError, ValueError):
        pass

    return None


def is_convertible(
    from_unit: str,
    to_unit: str,
    molecular_weight: Optional[float] = None,
) -> bool:
    """Quick compatibility check without converting a real value."""
    return normalise(1.0, from_unit, to_unit, molecular_weight) is not None


# ── Molar ↔ mass bridge ────────────────────────────────────────────────────

def _molar_mass_convert(
    value: float,
    src: pint.Unit,
    dst: pint.Unit,
    molecular_weight: float,
) -> Optional[float]:
    """Convert between molar (mol/L) and mass (g/L) concentrations.

    Bridge: mass = moles × MW (g/mol).
    """
    try:
        src_q = _ureg.Quantity(float(value), src)

        mass_dim = (_ureg.gram / _ureg.liter).dimensionality
        mole_dim = (_ureg.mole / _ureg.liter).dimensionality

        src_is_mass = src_q.dimensionality == mass_dim
        src_is_mole = src_q.dimensionality == mole_dim
        dst_is_mass = _ureg.Quantity(1, dst).dimensionality == mass_dim
        dst_is_mole = _ureg.Quantity(1, dst).dimensionality == mole_dim

        if not ((src_is_mass or src_is_mole) and (dst_is_mass or dst_is_mole)):
            return None

        if src_is_mass and dst_is_mole:
            g_per_l = src_q.to("gram / liter").magnitude
            mol_per_l = g_per_l / molecular_weight
            return float(_ureg.Quantity(mol_per_l, "mole / liter").to(dst).magnitude)

        if src_is_mole and dst_is_mass:
            mol_per_l = src_q.to("mole / liter").magnitude
            g_per_l = mol_per_l * molecular_weight
            return float(_ureg.Quantity(g_per_l, "gram / liter").to(dst).magnitude)

        return None
    except (pint.DimensionalityError, pint.UndefinedUnitError, ValueError):
        return None
