"""
Alias rule discovery.

Each module in this package can export an ``ALIAS_RULES`` list of callables.
Each callable receives a LOINC CSV row (dict) and returns
``list[tuple[str, str]]`` — ``(alias_text, source_tag)`` pairs.
"""
import importlib
import pkgutil
from collections.abc import Callable
from typing import Any

_cache: list[Callable[[dict[str, Any]], list[tuple[str, str]]]] | None = None


def discover_rules() -> list[Callable[[dict[str, Any]], list[tuple[str, str]]]]:
    global _cache
    if _cache is not None:
        return _cache

    rules: list[Callable] = []
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        mod_rules = getattr(mod, "ALIAS_RULES", None)
        if mod_rules:
            rules.extend(mod_rules)
    _cache = rules
    return rules
