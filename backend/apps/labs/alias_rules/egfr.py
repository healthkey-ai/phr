"""
eGFR alias rules.

Generates race- and formula-qualified aliases for eGFR LOINC codes so
that "eGFR CKD-EPI 2021" and "eGFR African American" resolve uniquely
instead of colliding on the bare "egfr" alias.
"""
from typing import Any

_EGFR_COMPONENT = "glomerular filtration rate"


def _is_egfr(row: dict[str, Any]) -> bool:
    comp = (row.get("COMPONENT") or "").lower()
    return _EGFR_COMPONENT in comp


def egfr_race_aliases(row: dict[str, Any]) -> list[tuple[str, str]]:
    if not _is_egfr(row):
        return []

    method = (row.get("METHOD_TYP") or "").lower()
    component = (row.get("COMPONENT") or "").lower()
    aliases: list[tuple[str, str]] = []

    is_black = "black" in component or "african" in component
    is_non_black = "non-black" in component or "non black" in component

    if "mdrd" in method:
        if is_non_black:
            aliases.append(("eGFR MDRD Non-Black", "rule:egfr"))
        elif is_black:
            aliases.append(("eGFR MDRD Black", "rule:egfr"))
            aliases.append(("eGFR MDRD African American", "rule:egfr"))
        else:
            aliases.append(("eGFR MDRD", "rule:egfr"))

    if "ckd-epi" in method or "ckd epi" in method:
        year = ""
        if "2021" in method or "2021" in component:
            year = " 2021"
        elif "2009" in method or "2009" in component:
            year = " 2009"

        if is_non_black:
            aliases.append((f"eGFR CKD-EPI{year} Non-Black", "rule:egfr"))
        elif is_black:
            aliases.append((f"eGFR CKD-EPI{year} Black", "rule:egfr"))
            aliases.append((f"eGFR CKD-EPI{year} African American", "rule:egfr"))
        else:
            aliases.append((f"eGFR CKD-EPI{year}", "rule:egfr"))

    return aliases


def egfr_formula_aliases(row: dict[str, Any]) -> list[tuple[str, str]]:
    if not _is_egfr(row):
        return []

    method = (row.get("METHOD_TYP") or "").lower()
    component = (row.get("COMPONENT") or "").lower()
    aliases: list[tuple[str, str]] = []

    is_cystatin = "cystatin" in component
    is_creatinine = "creatinine" in component or "creat" in component

    if is_cystatin and is_creatinine:
        aliases.append(("eGFRcr-cys", "rule:egfr"))
    elif is_cystatin:
        aliases.append(("eGFRcys", "rule:egfr"))
    elif is_creatinine:
        aliases.append(("eGFRcr", "rule:egfr"))

    if "2021" in method or "2021" in component:
        base = aliases[0][0] if aliases else "eGFR"
        aliases.append((f"{base} CKD-EPI 2021", "rule:egfr"))

    return aliases


ALIAS_RULES = [egfr_race_aliases, egfr_formula_aliases]
