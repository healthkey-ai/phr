"""
Labs v2 schema migration.

- New tables: LoincEntry, LoincAlias
- Renames: LabTestType→LabTestEntry, LabResult→LabValue,
  LabUpload→UploadJob, LabUploadFile→UploadFile
- LabTestEntry: drop category FK, loinc_code, reference_ranges;
  add loinc_entry FK
- LabValue: rename test_type→test_entry; add loinc_entry FK;
  update match_method/reference_source choices
- Delete LabCategory
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("labs", "0006_populate_name_normalized"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Create LOINC reference tables ─────────────────────────────
        migrations.CreateModel(
            name="LoincEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=16, unique=True, db_index=True)),
                ("component", models.CharField(max_length=128, blank=True, default="")),
                ("short_name", models.CharField(max_length=128, blank=True, default="")),
                ("long_name", models.CharField(max_length=256, blank=True, default="")),
                ("system", models.CharField(max_length=64, blank=True, default="")),
                ("default_unit", models.CharField(max_length=32, blank=True, default="")),
                ("unit_family", models.CharField(max_length=32, blank=True, default="")),
                ("category", models.CharField(max_length=64, blank=True, default="")),
                ("status", models.CharField(max_length=16, default="ACTIVE")),
                ("value_type", models.CharField(
                    max_length=16,
                    choices=[("numeric", "Numeric"), ("qualitative", "Qualitative"), ("ratio", "Ratio")],
                    default="numeric",
                )),
            ],
            options={
                "db_table": "labs_loincentry",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="LoincAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=256)),
                ("text_normalized", models.CharField(max_length=256, db_index=True)),
                ("source", models.CharField(
                    max_length=32,
                    choices=[
                        ("csv_extraction", "CSV extraction"),
                        ("alias_rule", "Alias rule"),
                        ("curated", "Curated"),
                    ],
                    default="csv_extraction",
                )),
                ("loinc_entry", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="aliases",
                    to="labs.loincentry",
                )),
            ],
            options={
                "db_table": "labs_loincalias",
            },
        ),
        migrations.AddIndex(
            model_name="loincalias",
            index=models.Index(fields=["text_normalized"], name="labs_loinca_text_no_360328_idx"),
        ),

        # ── 2. Remove old indexes and constraints ────────────────────────
        migrations.RemoveIndex(
            model_name="labtesttype",
            name="labs_labtes_loinc_c_9ff2ed_idx",
        ),
        migrations.RemoveConstraint(
            model_name="labtesttype",
            name="uniq_labs_labtesttype_loinc_code_when_set",
        ),
        migrations.RemoveIndex(
            model_name="labtesttype",
            name="labs_labtes_name_no_939f43_idx",
        ),
        migrations.RemoveIndex(
            model_name="labresult",
            name="labs_labres_user_id_528051_idx",
        ),
        migrations.RemoveIndex(
            model_name="labupload",
            name="labs_labupl_user_id_8c3214_idx",
        ),
        migrations.RemoveIndex(
            model_name="labuploadfile",
            name="labs_labupl_sha256_5f8828_idx",
        ),

        # ── 3. Drop category FK before deleting LabCategory ──────────────
        migrations.RemoveField(
            model_name="labtesttype",
            name="category",
        ),

        # ── 4. Rename Django models ──────────────────────────────────────
        migrations.RenameModel(old_name="LabTestType", new_name="LabTestEntry"),
        migrations.RenameModel(old_name="LabResult", new_name="LabValue"),
        migrations.RenameModel(old_name="LabUpload", new_name="UploadJob"),
        migrations.RenameModel(old_name="LabUploadFile", new_name="UploadFile"),

        # ── 5. Rename physical tables ────────────────────────────────────
        migrations.AlterModelTable(name="labtestentry", table="labs_labtestentry"),
        migrations.AlterModelTable(name="labvalue", table="labs_labvalue"),
        migrations.AlterModelTable(name="uploadjob", table="labs_uploadjob"),
        migrations.AlterModelTable(name="uploadfile", table="labs_uploadfile"),

        # ── 6. LabTestEntry field changes ────────────────────────────────
        migrations.RemoveField(model_name="labtestentry", name="loinc_code"),
        migrations.RemoveField(model_name="labtestentry", name="reference_ranges"),
        migrations.AddField(
            model_name="labtestentry",
            name="loinc_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="test_entries",
                to="labs.loincentry",
            ),
        ),
        migrations.AlterField(
            model_name="labtestentry",
            name="default_unit",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AlterModelOptions(
            name="labtestentry",
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.AlterField(
            model_name="labtestentry",
            name="molecular_weight",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="labtestentry",
            name="name_normalized",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
        ),
        migrations.AddIndex(
            model_name="labtestentry",
            index=models.Index(fields=["name_normalized"], name="labs_labtes_name_no_8299ed_idx"),
        ),

        # ── 7. LabValue field changes ────────────────────────────────────
        migrations.RenameField(
            model_name="labvalue",
            old_name="test_type",
            new_name="test_entry",
        ),
        migrations.AddField(
            model_name="labvalue",
            name="loinc_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lab_values",
                to="labs.loincentry",
            ),
        ),
        migrations.AlterField(
            model_name="labvalue",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lab_values",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="labvalue",
            name="upload",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="values",
                to="labs.uploadjob",
            ),
        ),
        migrations.AlterField(
            model_name="labvalue",
            name="test_entry",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="values",
                to="labs.labtestentry",
            ),
        ),
        migrations.AlterField(
            model_name="labvalue",
            name="match_method",
            field=models.CharField(
                choices=[
                    ("loinc", "LOINC direct (Tier 0)"),
                    ("alias_exact", "Alias exact match (Tier 1)"),
                    ("name_fallback", "Name fallback (stub)"),
                    ("manual", "Patient manually matched"),
                    ("unmatched", "Unmatched"),
                ],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="labvalue",
            name="reference_source",
            field=models.CharField(
                choices=[("report", "From report"), ("none", "No range")],
                default="none",
                max_length=8,
            ),
        ),
        migrations.AddIndex(
            model_name="labvalue",
            index=models.Index(
                fields=["user", "test_entry", "-measured_at"],
                name="labs_labval_user_id_a3ff1f_idx",
            ),
        ),

        # ── 8. UploadJob field changes ───────────────────────────────────
        migrations.AlterField(
            model_name="uploadjob",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="upload_jobs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="uploadjob",
            index=models.Index(
                fields=["user", "-created_at"],
                name="labs_upload_user_id_778882_idx",
            ),
        ),

        # ── 9. UploadFile index ──────────────────────────────────────────
        migrations.AddIndex(
            model_name="uploadfile",
            index=models.Index(
                fields=["sha256"],
                name="labs_upload_sha256_a9d729_idx",
            ),
        ),

        # ── 10. Delete LabCategory ───────────────────────────────────────
        migrations.DeleteModel(name="LabCategory"),
    ]
