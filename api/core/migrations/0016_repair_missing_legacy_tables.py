from django.db import migrations


MISSING_LEGACY_MODELS = [
    "OTP",
    "Review",
]


def create_missing_legacy_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name in MISSING_LEGACY_MODELS:
        model = apps.get_model("core", model_name)
        if model._meta.db_table in existing_tables:
            continue
        schema_editor.create_model(model)
        existing_tables.add(model._meta.db_table)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_repair_legacy_verificationrequest_document_url"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_legacy_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
