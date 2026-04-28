"""
prepare_alias_audit — Batch audit workflow for the /curate-loinc-aliases skill.

--prepare: Read Loinc.csv + existing fixture, split top 2000 codes into
           20 batches of 100, write build/alias_audit/batch_NNN.json.

--merge:   Read additions_NNN.json files, re-normalize, drop ambiguous,
           merge into curated_loinc_aliases.json fixture.

Usage:
    python manage.py prepare_alias_audit --prepare \
        --source Loinc.csv --fixture curated_loinc_aliases.json

    python manage.py prepare_alias_audit --merge \
        --fixture curated_loinc_aliases.json
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.labs.normalize import normalize

_AUDIT_DIR = Path("build/alias_audit")
_TOP_N = 2000
_BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Prepare or merge alias audit batches for the /curate-loinc-aliases skill."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--prepare", action="store_true")
        group.add_argument("--merge", action="store_true")

        parser.add_argument("--source", help="Path to Loinc.csv (required for --prepare)")
        parser.add_argument("--fixture", required=True, help="Path to curated_loinc_aliases.json")

    def handle(self, **options):
        if options["prepare"]:
            self._prepare(options)
        else:
            self._merge(options)

    def _prepare(self, options):
        source = options.get("source")
        if not source:
            raise CommandError("--source is required with --prepare")
        source = Path(source)
        fixture_path = Path(options["fixture"])

        # Load existing aliases grouped by loinc_num
        existing_by_code: dict[str, list[str]] = defaultdict(list)
        if fixture_path.exists():
            with fixture_path.open() as f:
                for entry in json.load(f):
                    existing_by_code[entry["loinc_num"]].append(entry["alias_normalized"])

        # Read CSV, collect qualifying codes with metadata
        codes: list[dict] = []
        with source.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                loinc_num = (row.get("LOINC_NUM") or "").strip()
                status = (row.get("STATUS") or "").strip()
                classtype = (row.get("CLASSTYPE") or "").strip()
                if not loinc_num or status not in ("ACTIVE", "TRIAL") or classtype != "1":
                    continue

                alias_count = len(existing_by_code.get(loinc_num, []))
                codes.append({
                    "loinc_num": loinc_num,
                    "component": (row.get("COMPONENT") or "").strip(),
                    "short_name": (row.get("SHORTNAME") or "").strip(),
                    "long_common_name": (row.get("LONG_COMMON_NAME") or "").strip(),
                    "system": (row.get("SYSTEM") or "").strip(),
                    "existing_aliases": existing_by_code.get(loinc_num, []),
                    "existing_alias_count": alias_count,
                })

        # Rank: catalog-tracked codes first, then common lab tests, then
        # the long tail.  "Msmt" archetype codes (108xxx+) are deprioritized.
        from apps.labs.models import LabTestEntry
        catalog_codes = set(
            LabTestEntry.objects
            .exclude(loinc_entry__isnull=True)
            .values_list("loinc_entry__code", flat=True)
        )

        _COMMON_SYSTEMS = {
            "Ser/Plas", "Ser", "Plas", "Bld", "Urine",
        }

        def _rank_key(c):
            ac = c["existing_alias_count"]
            is_catalog = c["loinc_num"] in catalog_codes
            is_msmt = "Msmt" in c["short_name"]
            in_common_sys = c["system"] in _COMMON_SYSTEMS

            # Tier 0: codes linked to our LabTestEntry catalog
            if is_catalog:
                return (0, ac, c["loinc_num"])
            # Tier 1: non-Msmt codes with aliases in common systems
            if not is_msmt and ac >= 1 and in_common_sys:
                return (1, ac, c["loinc_num"])
            # Tier 2: non-Msmt codes with aliases in any system
            if not is_msmt and ac >= 1:
                return (2, ac, c["loinc_num"])
            # Tier 3: Msmt codes and 0-alias codes
            return (3, ac, c["loinc_num"])

        codes.sort(key=_rank_key)
        top = codes[:_TOP_N]

        # Split into batches
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        batch_count = 0
        for i in range(0, len(top), _BATCH_SIZE):
            batch = top[i : i + _BATCH_SIZE]
            batch_file = _AUDIT_DIR / f"batch_{batch_count:03d}.json"
            with batch_file.open("w") as f:
                json.dump(batch, f, indent=2, ensure_ascii=False)
            batch_count += 1

        summary = {
            "batch_count": batch_count,
            "codes_per_batch": _BATCH_SIZE,
            "total_codes": len(top),
        }
        with (_AUDIT_DIR / "summary.json").open("w") as f:
            json.dump(summary, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Wrote {batch_count} batches ({len(top)} codes) to {_AUDIT_DIR}/"
        ))

    def _merge(self, options):
        fixture_path = Path(options["fixture"])
        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        with fixture_path.open() as f:
            fixture = json.load(f)

        # Build lookup of existing (loinc_num, alias_normalized) pairs
        existing_pairs: set[tuple[str, str]] = set()
        alias_to_codes: dict[str, set[str]] = defaultdict(set)
        for entry in fixture:
            pair = (entry["loinc_num"], entry["alias_normalized"])
            existing_pairs.add(pair)
            alias_to_codes[entry["alias_normalized"]].add(entry["loinc_num"])

        # Read all additions files
        additions_files = sorted(_AUDIT_DIR.glob("additions_*.json"))
        if not additions_files:
            self.stdout.write(self.style.WARNING("No additions files found"))
            return

        raw_additions = []
        for af in additions_files:
            with af.open() as f:
                raw_additions.extend(json.load(f))

        self.stdout.write(f"  Read {len(raw_additions)} raw additions from {len(additions_files)} files")

        # Re-normalize and filter
        new_alias_to_codes: dict[str, set[str]] = defaultdict(set)
        normalized_additions = []
        for add in raw_additions:
            norm = normalize(add["alias"])
            if not norm:
                continue
            loinc_num = add["loinc_num"]
            # Skip if already in fixture
            if (loinc_num, norm) in existing_pairs:
                continue
            new_alias_to_codes[norm].add(loinc_num)
            normalized_additions.append({
                "loinc_num": loinc_num,
                "alias": add["alias"],
                "alias_normalized": norm,
                "source_field": add.get("source_field", "curated_audit"),
            })

        # Drop additions whose normalized form conflicts with existing aliases on a different code
        conflicting = set()
        for norm, new_codes in new_alias_to_codes.items():
            existing_codes = alias_to_codes.get(norm, set())
            if existing_codes and new_codes != existing_codes:
                conflicting.add(norm)

        # Drop additions that are ambiguous among themselves
        self_ambiguous = {norm for norm, codes in new_alias_to_codes.items() if len(codes) > 1}
        drop = conflicting | self_ambiguous

        kept = [a for a in normalized_additions if a["alias_normalized"] not in drop]
        self.stdout.write(
            f"  Kept {len(kept)}, dropped {len(normalized_additions) - len(kept)} "
            f"({len(conflicting)} conflicting, {len(self_ambiguous)} self-ambiguous)"
        )

        # Append to fixture
        for a in kept:
            existing_pairs.add((a["loinc_num"], a["alias_normalized"]))
        fixture.extend(kept)
        fixture.sort(key=lambda e: (e["loinc_num"], e["alias_normalized"]))

        with fixture_path.open("w") as f:
            json.dump(fixture, f, ensure_ascii=False, indent=None, separators=(",", ":"))

        self.stdout.write(self.style.SUCCESS(
            f"Updated {fixture_path}: {len(fixture)} total aliases (+{len(kept)} new)"
        ))
