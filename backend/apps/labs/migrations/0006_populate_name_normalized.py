"""
Populate `LabTestType.name_normalized` for rows that predate the field.

Runs once after 0005 added the column. Idempotent (skips rows already
populated), reversible (clears the column). Doesn't depend on matching.py
so the migration works even if the loinc_common.json fixture is missing at
migrate time (migrations run as part of deploy, matching's fixture check
fires on first import — we inline normalize_name here to break that dep).
"""
import unicodedata

from django.db import migrations


def _normalize_name(raw: str) -> str:
    """Mirror of apps.labs.matching.normalize_name, inlined to keep this
    migration self-contained."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw)).casefold()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())


def forward(apps, schema_editor):
    LabTestType = apps.get_model("labs", "LabTestType")
    updates = []
    for row in LabTestType.objects.all().only("id", "name", "name_normalized"):
        normalized = _normalize_name(row.name)
        if row.name_normalized != normalized:
            row.name_normalized = normalized
            updates.append(row)
    if updates:
        LabTestType.objects.bulk_update(updates, ["name_normalized"])


def reverse(apps, schema_editor):
    LabTestType = apps.get_model("labs", "LabTestType")
    LabTestType.objects.update(name_normalized="")


class Migration(migrations.Migration):

    dependencies = [
        ("labs", "0005_remove_labtesttype_aliases_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
