"""
Unit-family classification and compatibility gate for LOINC matching.

Classifies incoming lab-report unit strings into one of 13 broad families,
then checks whether the incoming family is compatible with a LOINC entry's
unit_family.  Incompatible → reject the candidate, no matter how well the
name matches.

Families:
    mass_per_volume, molar_per_volume, cells_per_volume, percent, ratio,
    enzymatic_activity, hormone_activity, hematology_derived, pressure,
    volume_rate, mass_per_time, sed_rate, unknown
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")

# ── unit string → family ───────────────────────────────────────────────────
# Keys are normalised (lowercase, NFKD, µ→u, suffix-stripped).

_UNIT_TO_FAMILY: dict[str, str] = {
    # mass / volume
    "mg/dl": "mass_per_volume",
    "g/dl": "mass_per_volume",
    "g/l": "mass_per_volume",
    "mg/l": "mass_per_volume",
    "ng/ml": "mass_per_volume",
    "ng/dl": "mass_per_volume",
    "ng/l": "mass_per_volume",
    "pg/ml": "mass_per_volume",
    "pg/dl": "mass_per_volume",
    "ug/dl": "mass_per_volume",
    "ug/ml": "mass_per_volume",
    "ug/l": "mass_per_volume",
    "mcg/dl": "mass_per_volume",
    "mcg/ml": "mass_per_volume",
    # molar / volume
    "mmol/l": "molar_per_volume",
    "umol/l": "molar_per_volume",
    "nmol/l": "molar_per_volume",
    "pmol/l": "molar_per_volume",
    "mol/l": "molar_per_volume",
    "meq/l": "molar_per_volume",
    # cells / volume
    "10*3/ul": "cells_per_volume",
    "10*6/ul": "cells_per_volume",
    "10*9/l": "cells_per_volume",
    "10^3/ul": "cells_per_volume",
    "10^6/ul": "cells_per_volume",
    "10^9/l": "cells_per_volume",
    "10**3/ul": "cells_per_volume",
    "10**6/ul": "cells_per_volume",
    "10e3/ul": "cells_per_volume",
    "x10(3)/ul": "cells_per_volume",
    "x10(6)/ul": "cells_per_volume",
    "x10^3/ul": "cells_per_volume",
    "x10^6/ul": "cells_per_volume",
    "x10^9/l": "cells_per_volume",
    "k/ul": "cells_per_volume",
    "/ul": "cells_per_volume",
    "cells/ul": "cells_per_volume",
    "thousand/ul": "cells_per_volume",
    "million/ul": "cells_per_volume",
    "1000/ul": "cells_per_volume",
    # percent
    "%": "percent",
    "pct": "percent",
    "% of total": "percent",
    "% of total hgb": "percent",
    # ratio
    "ratio": "ratio",
    "{ratio}": "ratio",
    # enzymatic activity
    "u/l": "enzymatic_activity",
    "iu/l": "enzymatic_activity",
    "[iu]/l": "enzymatic_activity",
    "u/ml": "enzymatic_activity",
    "ku/l": "enzymatic_activity",
    "k[iu]/l": "enzymatic_activity",
    # hormone activity (IU/mL and milli/micro IU — TSH, insulin, etc.)
    "iu/ml": "hormone_activity",
    "[iu]/ml": "hormone_activity",
    "miu/l": "hormone_activity",
    "m[iu]/l": "hormone_activity",
    "mu/l": "hormone_activity",
    "uiu/ml": "hormone_activity",
    "u[iu]/ml": "hormone_activity",
    "uu/ml": "hormone_activity",
    "miu/ml": "hormone_activity",
    "mu/ml": "hormone_activity",
    # hematology derived (MCV, MCH)
    "fl": "hematology_derived",
    "pg": "hematology_derived",
    # pressure
    "mmhg": "pressure",
    "mm hg": "pressure",
    "kpa": "pressure",
    # volume rate (eGFR)
    "ml/min": "volume_rate",
    "ml/min/1.73m2": "volume_rate",
    "ml/min/{1.73_m2}": "volume_rate",
    "ml/min/1.73 m2": "volume_rate",
    # mass / time
    "mg/24h": "mass_per_time",
    "mg/d": "mass_per_time",
    "g/24h": "mass_per_time",
    "g/d": "mass_per_time",
    # sed rate
    "mm/h": "sed_rate",
    "mm/hr": "sed_rate",
}

# Families that are cross-compatible (convertible with molecular weight).
_CROSS_COMPATIBLE = frozenset({"mass_per_volume", "molar_per_volume"})


def _normalize_key(raw: str) -> str:
    s = unicodedata.normalize("NFKD", raw).casefold().strip()
    s = s.replace("µ", "u").replace("μ", "u")
    s = _SUFFIX_RE.sub("", s).strip()
    return " ".join(s.split())


@lru_cache(maxsize=256)
def classify_unit(raw: str | None) -> str:
    """Classify a unit string into a broad family. Returns ``"unknown"`` for
    unrecognised or empty strings."""
    if not raw:
        return "unknown"
    key = _normalize_key(raw)
    if not key:
        return "unknown"
    return _UNIT_TO_FAMILY.get(key, "unknown")


def units_compatible(family_a: str, family_b: str) -> bool:
    """Check whether two unit families are compatible.

    Rules:
      - same family → compatible
      - either side is ``""`` or ``"unknown"`` → compatible (permissive)
      - mass_per_volume ↔ molar_per_volume → compatible (MW bridge)
      - everything else → incompatible
    """
    if not family_a or family_a == "unknown":
        return True
    if not family_b or family_b == "unknown":
        return True
    if family_a == family_b:
        return True
    if {family_a, family_b} <= _CROSS_COMPATIBLE:
        return True
    return False
