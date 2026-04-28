"""
fix_stale_units — Sync default_unit from LoincEntry → LabTestEntry.

Fixes LabTestEntries whose default_unit drifted from their linked
LoincEntry (e.g. created via name_fallback with the first upload's unit,
then later linked to a LOINC code with a different canonical unit).

Only updates when the old unit is convertible to the LOINC unit
(or was blank), so UCUM-only units like [arb'U] won't overwrite
real lab-report units like U/mL.

Usage:
    python manage.py fix_stale_units          # dry-run (default)
    python manage.py fix_stale_units --apply  # actually update rows
"""
import time

from django.core.management.base import BaseCommand

from apps.labs.models import LabTestEntry
from apps.labs.unit_converter import is_convertible


class Command(BaseCommand):
    help = "Sync default_unit from LoincEntry → linked LabTestEntries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default is dry-run)",
        )

    def handle(self, **options):
        apply = options["apply"]
        t0 = time.monotonic()

        qs = (
            LabTestEntry.objects
            .filter(loinc_entry__isnull=False)
            .select_related("loinc_entry")
        )

        fixed = 0
        skipped = 0

        for te in qs.iterator():
            loinc_unit = te.loinc_entry.default_unit
            if not loinc_unit or te.default_unit == loinc_unit:
                continue

            if te.default_unit and not is_convertible(te.default_unit, loinc_unit):
                skipped += 1
                self.stdout.write(
                    f"  SKIP {te.abbreviation}: {te.default_unit!r} → {loinc_unit!r} (not convertible)"
                )
                continue

            old = te.default_unit or "(empty)"
            if apply:
                te.default_unit = loinc_unit
                te.save(update_fields=["default_unit"])

            fixed += 1
            tag = "FIXED" if apply else "WOULD FIX"
            self.stdout.write(f"  {tag} {te.abbreviation}: {old!r} → {loinc_unit!r}")

        elapsed = time.monotonic() - t0
        mode = "applied" if apply else "dry-run"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done ({mode}): {fixed} fixed, {skipped} skipped (not convertible) in {elapsed:.1f}s"
            )
        )
