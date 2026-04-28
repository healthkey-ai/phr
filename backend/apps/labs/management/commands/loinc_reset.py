"""
loinc_reset — Full pipeline orchestrator: wipe + sync + load aliases + link.

Usage:
    python manage.py loinc_reset --bundle ../loinc-codes-aliases.zip --yes
    python manage.py loinc_reset --csv Loinc.csv --aliases curated_loinc_aliases.json --yes
"""
import json
import tempfile
import time
import zipfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.labs.models import LabTestEntry, LabValue, LoincAlias, LoincEntry
from apps.labs.normalize import normalize, normalize_loinc


class Command(BaseCommand):
    help = "Wipe and reload all LOINC data (LoincEntry + LoincAlias)."

    def add_arguments(self, parser):
        parser.add_argument("--bundle", help="Path to loinc-codes-aliases.zip")
        parser.add_argument("--csv", help="Path to Loinc.csv")
        parser.add_argument("--aliases", help="Path to curated_loinc_aliases.json")
        parser.add_argument("--classes", help="Path to LoincClass.csv")
        parser.add_argument("--yes", action="store_true", help="Skip confirmation")

    def handle(self, **options):
        csv_path, aliases_path, classes_path, tmpdir = self._resolve_paths(options)

        if not options["yes"]:
            self.stderr.write(
                "This will DELETE all LoincEntry + LoincAlias rows and reload from scratch."
            )
            if input("Continue? [y/N] ").strip().lower() != "y":
                self.stderr.write("Aborted.")
                return

        try:
            t0 = time.monotonic()

            self._wipe()
            self._sync_csv(csv_path, classes_path)
            self._load_aliases(aliases_path)
            self._link_test_entries()

            elapsed = time.monotonic() - t0
            self.stdout.write(self.style.SUCCESS(f"loinc_reset completed in {elapsed:.1f}s"))
        finally:
            if tmpdir:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _resolve_paths(self, options):
        tmpdir = None
        classes_path = None
        if options.get("bundle"):
            bundle = Path(options["bundle"])
            if not bundle.exists():
                raise CommandError(f"Bundle not found: {bundle}")
            tmpdir = tempfile.mkdtemp(prefix="loinc_reset_")
            with zipfile.ZipFile(bundle) as zf:
                zf.extract("Loinc.csv", tmpdir)
                zf.extract("curated_loinc_aliases.json", tmpdir)
                if "LoincClass.csv" in zf.namelist():
                    zf.extract("LoincClass.csv", tmpdir)
                    classes_path = Path(tmpdir) / "LoincClass.csv"
            csv_path = Path(tmpdir) / "Loinc.csv"
            aliases_path = Path(tmpdir) / "curated_loinc_aliases.json"
        elif options.get("csv") and options.get("aliases"):
            csv_path = Path(options["csv"])
            aliases_path = Path(options["aliases"])
            if not csv_path.exists():
                raise CommandError(f"CSV not found: {csv_path}")
            if not aliases_path.exists():
                raise CommandError(f"Aliases not found: {aliases_path}")
        else:
            raise CommandError("Provide --bundle OR both --csv and --aliases")
        if options.get("classes"):
            classes_path = Path(options["classes"])
        return csv_path, aliases_path, classes_path, tmpdir

    def _wipe(self):
        self.stdout.write("[wipe] Clearing LOINC data...")
        t0 = time.monotonic()
        with transaction.atomic():
            LoincAlias.objects.all().delete()
            LabValue.objects.filter(loinc_entry__isnull=False).update(loinc_entry=None)
            LabTestEntry.objects.filter(loinc_entry__isnull=False).update(loinc_entry=None)
            LoincEntry.objects.all().delete()
        self.stdout.write(f"  wipe done in {time.monotonic() - t0:.1f}s")

    def _sync_csv(self, csv_path: Path, classes_path: Path | None):
        self.stdout.write("[1/3] sync_loinc_csv...")
        kwargs = {"csv": str(csv_path), "verbosity": 1, "stdout": self.stdout}
        if classes_path:
            kwargs["classes"] = str(classes_path)
        call_command("sync_loinc_csv", **kwargs)

    def _load_aliases(self, aliases_path: Path):
        self.stdout.write("[2/3] load_aliases...")
        t0 = time.monotonic()

        with aliases_path.open() as f:
            data = json.load(f)

        # Build code→LoincEntry pk lookup
        code_to_pk: dict[str, int] = {}
        for entry in LoincEntry.objects.values_list("code", "pk"):
            code_to_pk[entry[0]] = entry[1]

        batch: list[LoincAlias] = []
        skipped = 0
        batch_size = 2000

        for item in data:
            loinc_num = item["loinc_num"]
            pk = code_to_pk.get(loinc_num)
            if pk is None:
                skipped += 1
                continue

            text_normalized = normalize(item["alias"])
            if not text_normalized:
                skipped += 1
                continue

            batch.append(LoincAlias(
                loinc_entry_id=pk,
                text=item["alias"][:256],
                text_normalized=text_normalized[:256],
                source=self._map_source(item.get("source_field", "")),
            ))

            if len(batch) >= batch_size:
                self._flush_alias_batch(batch)
                batch = []

        if batch:
            self._flush_alias_batch(batch)

        elapsed = time.monotonic() - t0
        loaded = LoincAlias.objects.count()
        self.stdout.write(f"  loaded {loaded} aliases, skipped {skipped} in {elapsed:.1f}s")

    def _flush_alias_batch(self, batch: list[LoincAlias]):
        with transaction.atomic():
            LoincAlias.objects.bulk_create(batch, ignore_conflicts=True)

    def _map_source(self, source_field: str) -> str:
        if source_field.startswith("rule:"):
            return "alias_rule"
        if source_field == "curated_audit":
            return "curated"
        return "csv_extraction"

    def _link_test_entries(self):
        self.stdout.write("[3/3] link_test_entries...")
        t0 = time.monotonic()

        # Strategy 1: Match via loinc_common.json fixture codes
        from apps.labs.matching import LOINC_COMMON
        linked = 0
        for code, fixture_entry in LOINC_COMMON.items():
            loinc = LoincEntry.objects.filter(code=code).first()
            if not loinc:
                continue
            name_norm = normalize_loinc_name(fixture_entry["loinc_short_name"])
            updated = LabTestEntry.objects.filter(
                name_normalized=name_norm,
                loinc_entry__isnull=True,
            ).update(loinc_entry=loinc)
            linked += updated

        # Strategy 2: Match by exact name_normalized against LoincEntry.short_name
        unlinked = LabTestEntry.objects.filter(loinc_entry__isnull=True)
        for test_entry in unlinked.iterator():
            if not test_entry.name_normalized:
                continue
            from apps.labs.normalize import normalize_name
            matches = LoincEntry.objects.filter(
                short_name__isnull=False,
            ).extra(
                where=["LOWER(short_name) = %s"],
                params=[test_entry.name.lower()],
            )[:2]
            match_list = list(matches)
            if len(match_list) == 1:
                test_entry.loinc_entry = match_list[0]
                test_entry.save(update_fields=["loinc_entry"])
                linked += 1

        # Sync default_unit from LoincEntry → LabTestEntry (only when convertible)
        from apps.labs.unit_converter import is_convertible
        for te in LabTestEntry.objects.filter(
            loinc_entry__isnull=False,
        ).select_related("loinc_entry").iterator():
            loinc_unit = te.loinc_entry.default_unit
            if loinc_unit and te.default_unit != loinc_unit:
                if not te.default_unit or is_convertible(te.default_unit, loinc_unit):
                    te.default_unit = loinc_unit
                    te.save(update_fields=["default_unit"])

        # Propagate to LabValue
        propagated = 0
        for lv in LabValue.objects.filter(
            loinc_entry__isnull=True,
            test_entry__loinc_entry__isnull=False,
        ).select_related("test_entry").iterator():
            lv.loinc_entry = lv.test_entry.loinc_entry
            lv.save(update_fields=["loinc_entry"])
            propagated += 1

        elapsed = time.monotonic() - t0
        self.stdout.write(f"  linked {linked} test entries, propagated {propagated} lab values in {elapsed:.1f}s")


def normalize_loinc_name(raw: str) -> str:
    from apps.labs.normalize import normalize_name
    return normalize_name(raw)
