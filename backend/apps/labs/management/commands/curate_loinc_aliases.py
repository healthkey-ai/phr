"""
curate_loinc_aliases — Extract aliases from Loinc.csv, resolve ambiguity,
write the curated fixture file.

Phase 1: CSV field extraction (COMPONENT, LONG_COMMON_NAME, SHORTNAME,
         CONSUMER_NAME, DisplayName, RELATEDNAMES2)
Phase 2: Alias rules (apps/labs/alias_rules/)
Phase 3: Ambiguity filter — drop normalized aliases that map to >1 code

Usage:
    python manage.py curate_loinc_aliases --source /path/to/Loinc.csv
    python manage.py curate_loinc_aliases --source Loinc.csv --output out.json
"""
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.labs.alias_rules import discover_rules
from apps.labs.normalize import normalize


_EXTRACT_FIELDS = [
    "COMPONENT",
    "LONG_COMMON_NAME",
    "SHORTNAME",
    "CONSUMER_NAME",
    "DisplayName",
]

_SPLIT_FIELD = "RELATEDNAMES2"


class Command(BaseCommand):
    help = "Extract aliases from Loinc.csv, resolve ambiguity, write fixture."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="Path to Loinc.csv")
        parser.add_argument(
            "--output",
            default="curated_loinc_aliases.json",
            help="Output fixture path (default: curated_loinc_aliases.json)",
        )
        parser.add_argument("--report", default=None, help="Report JSON path")
        parser.add_argument(
            "--status",
            nargs="+",
            default=["ACTIVE", "TRIAL"],
            help="LOINC statuses to include",
        )

    def handle(self, **options):
        source = Path(options["source"])
        output = Path(options["output"])
        report_path = Path(options["report"]) if options["report"] else output.with_name("curate_report.json")
        allowed_statuses = set(options["status"])

        t0 = time.monotonic()

        # Phase 1 + 2: extract candidates
        candidates, total_qualifying = self._extract(source, allowed_statuses)
        self.stdout.write(f"  Phase 1+2: {len(candidates)} candidates from {total_qualifying} qualifying codes")

        # Phase 3: ambiguity filter
        kept, ambiguous_count, ambiguous_examples = self._filter_ambiguous(candidates)
        self.stdout.write(f"  Phase 3: kept {len(kept)}, dropped {ambiguous_count} ambiguous aliases")

        # Build output
        fixture = self._build_fixture(kept)
        codes_with_aliases = len({e["loinc_num"] for e in fixture})
        coverage_pct = round(codes_with_aliases / total_qualifying * 100, 1) if total_qualifying else 0

        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w") as f:
            json.dump(fixture, f, ensure_ascii=False, indent=None, separators=(",", ":"))

        report = {
            "total_qualifying_codes": total_qualifying,
            "total_aliases_kept": len(fixture),
            "codes_with_aliases": codes_with_aliases,
            "coverage_pct": coverage_pct,
            "ambiguous_aliases_dropped": ambiguous_count,
            "ambiguous_examples": dict(list(ambiguous_examples.items())[:20]),
        }
        with report_path.open("w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        elapsed = time.monotonic() - t0
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(fixture)} aliases to {output} in {elapsed:.1f}s"
        ))

    def _extract(self, source: Path, allowed_statuses: set[str]):
        candidates: list[tuple[str, str, str, str]] = []
        rules = discover_rules()
        qualifying_codes: set[str] = set()

        with source.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                loinc_num = (row.get("LOINC_NUM") or "").strip()
                status = (row.get("STATUS") or "").strip()
                classtype = (row.get("CLASSTYPE") or "").strip()

                if not loinc_num or status not in allowed_statuses:
                    continue
                if classtype != "1":
                    continue

                qualifying_codes.add(loinc_num)
                seen_normalized: set[str] = set()

                # Phase 1: CSV field extraction
                for field in _EXTRACT_FIELDS:
                    raw = (row.get(field) or "").strip()
                    if not raw:
                        continue
                    norm = normalize(raw)
                    if not norm or norm in seen_normalized:
                        continue
                    seen_normalized.add(norm)
                    candidates.append((norm, loinc_num, raw, field))

                # RELATEDNAMES2: semicolon-split
                related = (row.get(_SPLIT_FIELD) or "").strip()
                if related:
                    for part in related.split(";"):
                        part = part.strip()
                        if not part:
                            continue
                        norm = normalize(part)
                        if not norm or norm in seen_normalized:
                            continue
                        seen_normalized.add(norm)
                        candidates.append((norm, loinc_num, part, _SPLIT_FIELD))

                # Phase 2: alias rules
                for rule in rules:
                    for alias_text, source_tag in rule(row):
                        norm = normalize(alias_text)
                        if not norm or norm in seen_normalized:
                            continue
                        seen_normalized.add(norm)
                        candidates.append((norm, loinc_num, alias_text, source_tag))

        return candidates, len(qualifying_codes)

    def _filter_ambiguous(self, candidates):
        by_alias: dict[str, set[str]] = defaultdict(set)
        for norm, loinc_num, _raw, _field in candidates:
            by_alias[norm].add(loinc_num)

        ambiguous = {
            norm: sorted(codes)
            for norm, codes in by_alias.items()
            if len(codes) > 1
        }

        kept = [c for c in candidates if c[0] not in ambiguous]
        return kept, len(ambiguous), ambiguous

    def _build_fixture(self, kept):
        seen: set[tuple[str, str]] = set()
        fixture = []
        for norm, loinc_num, raw, field in kept:
            key = (loinc_num, norm)
            if key in seen:
                continue
            seen.add(key)
            fixture.append({
                "loinc_num": loinc_num,
                "alias": raw,
                "alias_normalized": norm,
                "source_field": field,
            })
        fixture.sort(key=lambda e: (e["loinc_num"], e["alias_normalized"]))
        return fixture
