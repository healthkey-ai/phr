"""
pack_loinc_bundle — Create or update loinc-codes-aliases.zip.

Bundles Loinc.csv + curated_loinc_aliases.json (+ optional report) into
a single zip that loinc_reset can consume.

Usage:
    python manage.py pack_loinc_bundle \
        --csv Loinc.csv --aliases curated_loinc_aliases.json --version 2.82
"""
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Pack Loinc.csv + curated aliases into loinc-codes-aliases.zip."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to Loinc.csv")
        parser.add_argument("--aliases", required=True, help="Path to curated_loinc_aliases.json")
        parser.add_argument("--classes", default=None, help="Path to LoincClass.csv")
        parser.add_argument("--report", default=None, help="Path to curate_report.json")
        parser.add_argument("--loinc-version", default=None, help="LOINC version string")
        parser.add_argument(
            "--output",
            default=None,
            help="Output zip path (default: ../loinc-codes-aliases.zip)",
        )

    def handle(self, **options):
        csv_path = Path(options["csv"])
        aliases_path = Path(options["aliases"])
        classes_path = Path(options["classes"]) if options["classes"] else None
        report_path = Path(options["report"]) if options["report"] else None

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")
        if not aliases_path.exists():
            raise CommandError(f"Aliases not found: {aliases_path}")
        if classes_path and not classes_path.exists():
            raise CommandError(f"Classes not found: {classes_path}")

        output = Path(options["output"]) if options["output"] else Path("../loinc-codes-aliases.zip")
        output = output.resolve()

        version = options.get("loinc_version") or self._detect_version(csv_path)

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(csv_path, "Loinc.csv")
            zf.write(aliases_path, "curated_loinc_aliases.json")
            if classes_path:
                zf.write(classes_path, "LoincClass.csv")
            if report_path and report_path.exists():
                zf.write(report_path, "curate_report.json")
            zf.writestr("VERSION", version)

        size_mb = output.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f"Packed {output} ({size_mb:.1f} MB) — LOINC {version}"
        ))

    def _detect_version(self, csv_path: Path) -> str:
        name = csv_path.parent.name
        for part in name.replace("_", " ").replace("-", " ").split():
            if part and part[0].isdigit() and "." in part:
                return part
        return "unknown"
