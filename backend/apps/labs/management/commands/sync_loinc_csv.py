"""
sync_loinc_csv — Parse Loinc.csv and upsert rows into LoincEntry.

Batched bulk_create with update_conflicts for crash-safe incremental loads.
After all batches: stale sweep removes codes not in the incoming set.

Usage:
    python manage.py sync_loinc_csv --csv /path/to/Loinc.csv
"""
import csv
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.labs.models import LoincEntry

_PROPERTY_TO_UNIT_FAMILY: dict[str, str] = {
    "MCnc": "mass_per_volume",
    "SCnc": "molar_per_volume",
    "CCnc": "enzymatic_activity",
    "NCnc": "cells_per_volume",
    "VRat": "volume_rate",
    "ArVRat": "volume_rate",
    "MRat": "mass_per_time",
}

_FRACTION_PROPERTIES = {"NFr", "MFr", "AFr", "VFr", "CFr", "SFr"}
_RATIO_PROPERTIES = {
    "SRto", "MRto", "NRto", "CRto", "VRto", "TRto", "LnRto", "RelRto", "Ratio",
}

_UPDATE_FIELDS = [
    "component", "short_name", "long_name", "system",
    "default_unit", "unit_family", "category", "status", "value_type",
]

def _load_class_names(classes_path) -> dict[str, str]:
    if not classes_path:
        return {}
    result: dict[str, str] = {}
    with classes_path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("CLASS") or "").strip()
            name = (row.get("DISPLAY_NAME") or "").strip()
            if code and name:
                result[code] = name
    return result


def _infer_unit_family(prop: str) -> str:
    if prop in _PROPERTY_TO_UNIT_FAMILY:
        return _PROPERTY_TO_UNIT_FAMILY[prop]
    base = prop.split(".")[0]
    if base in _FRACTION_PROPERTIES:
        return "percent"
    if base in _RATIO_PROPERTIES or prop in _RATIO_PROPERTIES:
        return "ratio"
    return ""


def _infer_value_type(scale_typ: str) -> str:
    if scale_typ in ("Ord", "Nom"):
        return "qualitative"
    return "numeric"


def _first_unit(example_ucum: str) -> str:
    if not example_ucum:
        return ""
    return example_ucum.split(";")[0].strip()[:32]


class Command(BaseCommand):
    help = "Parse Loinc.csv and upsert rows into the LoincEntry table."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to Loinc.csv")
        parser.add_argument("--classes", default=None, help="Path to LoincClass.csv")
        parser.add_argument(
            "--status",
            nargs="+",
            default=["ACTIVE", "TRIAL"],
            help="LOINC statuses to include",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Rows per bulk_create batch",
        )

    def handle(self, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        classes_path = Path(options["classes"]) if options.get("classes") else None
        class_names = _load_class_names(classes_path)
        if class_names:
            self.stdout.write(f"  loaded {len(class_names)} class display names")

        allowed_statuses = set(options["status"])
        batch_size = options["batch_size"]

        t0 = time.monotonic()
        incoming_codes: set[str] = set()
        batch: list[LoincEntry] = []
        total_upserted = 0

        with csv_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                loinc_num = (row.get("LOINC_NUM") or "").strip()
                status = (row.get("STATUS") or "").strip()
                classtype = (row.get("CLASSTYPE") or "").strip()

                if not loinc_num or status not in allowed_statuses:
                    continue
                if classtype != "1":
                    continue

                incoming_codes.add(loinc_num)
                prop = (row.get("PROPERTY") or "").strip()
                scale = (row.get("SCALE_TYP") or "").strip()

                entry = LoincEntry(
                    code=loinc_num,
                    component=(row.get("COMPONENT") or "")[:128],
                    short_name=(row.get("SHORTNAME") or "")[:128],
                    long_name=(row.get("LONG_COMMON_NAME") or "")[:256],
                    system=(row.get("SYSTEM") or "")[:64],
                    default_unit=_first_unit(row.get("EXAMPLE_UCUM_UNITS") or ""),
                    unit_family=_infer_unit_family(prop),
                    category=class_names.get(raw_class, raw_class)[:64] if (raw_class := (row.get("CLASS") or "").strip()) else "",
                    status=status[:16],
                    value_type=_infer_value_type(scale),
                )
                batch.append(entry)

                if len(batch) >= batch_size:
                    self._flush_batch(batch)
                    total_upserted += len(batch)
                    batch = []

        if batch:
            self._flush_batch(batch)
            total_upserted += len(batch)

        # Stale sweep
        stale_count = 0
        with transaction.atomic():
            stale = LoincEntry.objects.exclude(code__in=incoming_codes)
            stale_count = stale.count()
            if stale_count:
                stale.delete()

        elapsed = time.monotonic() - t0
        self.stdout.write(self.style.SUCCESS(
            f"sync_loinc_csv: {total_upserted} upserted, {stale_count} stale deleted "
            f"({len(incoming_codes)} codes) in {elapsed:.1f}s"
        ))

    def _flush_batch(self, batch: list[LoincEntry]):
        with transaction.atomic():
            LoincEntry.objects.bulk_create(
                batch,
                update_conflicts=True,
                unique_fields=["code"],
                update_fields=_UPDATE_FIELDS,
            )
