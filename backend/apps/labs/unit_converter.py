"""
Unit normalisation for lab values.

Design source: docs/patient-app-lab-upload-design.md §8.
Uses `pint` for dimensional analysis; extends the base registry with
lab-specific units (10^3/uL, K/uL, mEq/L, IU, etc.) that pint doesn't
know about out of the box.

Molar ↔ mass conversions require a molecular weight (g/mol), which is
stored per-test in LabTestType.molecular_weight.

Contract:
    normalise(value, from_unit, to_unit, molecular_weight=None) -> float | None

Returns None (rather than raising) on any failure so the caller can decide
how to surface the issue to the user — the review UI unchecks the row and
asks the patient to correct the unit manually.
"""
from __future__ import annotations

import math
import unicodedata
from typing import Optional

import pint

# ── Registry setup ────────────────────────────────────────────────────────────

_ureg = pint.UnitRegistry()

# Cell counts — lab reports use 10^3/uL, K/uL, 10^9/L interchangeably.
# Pint doesn't ship with these; define one canonical unit and let the alias
# map route every notation to the same target so conversions are a no-op.
_ureg.define("thousand_per_uL = 1000 / microliter")
_ureg.define("million_per_uL = 1e6 / microliter")

# International Units (for enzyme activity + hormone assays). Dimensionless
# in pint's view; we treat U/L as its own dimension so U/L ↔ IU/L round-trips
# cleanly, and define mIU / uIU explicitly because pint's short prefix parser
# doesn't accept `u` for micro.
_ureg.define("enzyme_activity = [enzyme]")
_ureg.define("U = enzyme_activity = IU")
_ureg.define("mIU = 0.001 * U")
_ureg.define("uIU = 0.000001 * U")
_ureg.define("lab_percent = [percentage]")
_ureg.define("percent_unit = lab_percent = % = pct")

# Milliequivalents per litre (charge-based concentration). For monovalent ions
# (Na, K, Cl) mEq/L == mmol/L numerically. For Phase 2a we only need Ca where
# conversion needs molecular weight + valence (2). Handle in _molar_mass_convert.
_ureg.define("milliequivalent = 0.001 * equivalent = mEq")
_ureg.define("equivalent = 1 * mole = eq")

# Ratio (unitless). Used for FLC ratio.
_ureg.define("ratio = dimensionless")


# ── Alias map — canonicalises messy lab-report unit strings to pint form ──────
# Run before pint parse. Lab reports are wildly inconsistent about casing,
# whitespace, micron symbols, slashes vs dots, and so on.
UNIT_ALIASES: dict[str, str] = {
    # Micro symbol variants (NFKD decomposes µ → u, but lab reports also use mc)
    "ug": "microgram",
    "μg": "microgram",
    "mcg": "microgram",
    "ul": "microliter",
    "μl": "microliter",
    "mcl": "microliter",
    "umol": "micromole",
    "μmol": "micromole",
    "mcmol": "micromole",
    # Cell-count notations — all route to thousand_per_uL (SI-equivalent)
    "k/ul": "thousand_per_uL",
    "10^3/ul": "thousand_per_uL",
    "10**3/ul": "thousand_per_uL",
    "10e3/ul": "thousand_per_uL",
    "1000/ul": "thousand_per_uL",
    "10^9/l": "thousand_per_uL",    # 10^9/L == 10^3/µL numerically
    "10**9/l": "thousand_per_uL",
    "10^6/ul": "million_per_uL",
    "10**6/ul": "million_per_uL",
    "m/ul": "million_per_uL",
    # Mass / volume
    "mg/dl": "milligram / deciliter",
    "g/dl": "gram / deciliter",
    "ng/ml": "nanogram / milliliter",
    "ng/dl": "nanogram / deciliter",
    "pg/ml": "picogram / milliliter",
    "pg/dl": "picogram / deciliter",
    "mg/l": "milligram / liter",
    "g/l": "gram / liter",
    "mmol/l": "millimole / liter",
    "umol/l": "micromole / liter",
    "μmol/l": "micromole / liter",
    "mcmol/l": "micromole / liter",
    "nmol/l": "nanomole / liter",
    "pmol/l": "picomole / liter",
    # Enzyme / hormone activity
    "u/l": "U / liter",
    "iu/l": "U / liter",
    "iu/ml": "U / milliliter",
    "u/ml": "U / milliliter",
    # TSH and similar hormone assays use mIU/L (lab standard) or uIU/mL (older US).
    # mIU and uIU are defined as explicit units in the registry above so both
    # round-trip cleanly.
    "miu/l": "mIU / liter",
    "miu/ml": "mIU / milliliter",
    "uiu/l": "uIU / liter",
    "uiu/ml": "uIU / milliliter",
    # Percent
    "%": "percent_unit",
    "pct": "percent_unit",
    # Time
    "ms": "millisecond",
    "sec": "second",
    "min": "minute",
    # mEq
    "meq/l": "milliequivalent / liter",
    # Ratio / dimensionless
    "ratio": "ratio",
    # Urine
    "mg/24h": "milligram",   # per-24h is a time window, not a unit — drop for comparison
}


# ── Public API ────────────────────────────────────────────────────────────────

def _canonicalise(unit: str) -> str:
    """Lowercase + strip + NFKD-fold + alias-lookup the unit string.

    Always returns a pint-parseable string. Returns "" for None/empty input
    (rather than silently treating it as "ratio" — that bit us once)."""
    if unit is None or unit == "":
        return ""
    s = unicodedata.normalize("NFKD", unit).casefold().strip()
    # U+00B5 (MICRO SIGN) and U+03BC (GREEK SMALL LETTER MU) don't always NFKD
    # to "u" — explicit replacement so µg matches ug matches mcg.
    s = s.replace("\u00b5", "u").replace("\u03bc", "u")
    # Strip common whitespace variations inside the unit
    s = " ".join(s.split())
    if not s:
        return ""
    # Alias table first (full-string match), then fallback to raw
    return UNIT_ALIASES.get(s, s)


def normalise(
    value: float,
    from_unit: str,
    to_unit: str,
    molecular_weight: Optional[float] = None,
) -> Optional[float]:
    """Convert `value` from `from_unit` to `to_unit`.

    Returns:
        The converted float value, or None if:
          - inputs are None / NaN
          - either unit can't be canonicalised
          - pint raises (dimensional mismatch without MW, unknown unit)
          - molar↔mass conversion was required but MW wasn't supplied
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None

    src_canonical = _canonicalise(from_unit)
    dst_canonical = _canonicalise(to_unit)

    if not src_canonical or not dst_canonical:
        return None

    # Fast path: identical canonical strings
    if src_canonical == dst_canonical:
        return float(value)

    try:
        src = _ureg.Quantity(float(value), src_canonical)
        return float(src.to(dst_canonical).magnitude)
    except (pint.errors.DimensionalityError, pint.errors.UndefinedUnitError, ValueError):
        pass

    # Molar↔mass fallback. Requires molecular weight in g/mol.
    if molecular_weight is not None and molecular_weight > 0:
        return _molar_mass_convert(value, src_canonical, dst_canonical, molecular_weight)

    return None


def _molar_mass_convert(
    value: float,
    from_unit: str,
    to_unit: str,
    molecular_weight: float,
) -> Optional[float]:
    """Convert between molar (mol/L) and mass (g/L) concentrations.

    The bridge is: mass = moles × MW (g/mol).

    Examples:
        creatinine: 1 mg/dL × (1 / 113.12) = 0.00884 mmol/L ≈ 88.4 µmol/L
        calcium:    1 mmol/L × 40.08       = 40.08 mg/L    ≈ 4.01 mg/dL
    """
    try:
        # Determine whether from_unit is mass-based or mole-based
        src_q = _ureg.Quantity(float(value), from_unit)
        dst_q_sample = _ureg.Quantity(1.0, to_unit)

        mass_dim = _ureg.gram / _ureg.liter
        mole_dim = _ureg.mole / _ureg.liter

        src_is_mass = src_q.dimensionality == mass_dim.dimensionality
        src_is_mole = src_q.dimensionality == mole_dim.dimensionality
        dst_is_mass = dst_q_sample.dimensionality == mass_dim.dimensionality
        dst_is_mole = dst_q_sample.dimensionality == mole_dim.dimensionality

        if not ((src_is_mass or src_is_mole) and (dst_is_mass or dst_is_mole)):
            return None

        # Mass → mole: divide by MW (g/mol)
        if src_is_mass and dst_is_mole:
            mass_per_l = src_q.to("gram / liter").magnitude
            moles_per_l = mass_per_l / molecular_weight
            return float((moles_per_l * _ureg("mole / liter")).to(to_unit).magnitude)

        # Mole → mass: multiply by MW
        if src_is_mole and dst_is_mass:
            moles_per_l = src_q.to("mole / liter").magnitude
            mass_per_l = moles_per_l * molecular_weight
            return float((mass_per_l * _ureg("gram / liter")).to(to_unit).magnitude)

        return None
    except (pint.errors.DimensionalityError, pint.errors.UndefinedUnitError, ValueError):
        return None


def is_convertible(from_unit: str, to_unit: str, molecular_weight: Optional[float] = None) -> bool:
    """Quick compatibility check without actually converting a value."""
    return normalise(1.0, from_unit, to_unit, molecular_weight) is not None
