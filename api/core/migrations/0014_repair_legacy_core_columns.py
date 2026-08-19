from django.db import migrations


LEGACY_MODEL_FIELDS = {
    "TutorProfile": [
        "profile_photo_url",
        "response_time",
    ],
    "VerificationRequest": [
        "document_urls",
        "nin_number",
        "principal_name",
        "profile_photo_url",
        "qualification",
        "school_address",
        "school_name",
    ],
    "Conversation": [
        "is_blocked",
    ],
}


def add_missing_columns(model, field_names, schema_editor):
    connection = schema_editor.connection
    table_name = model._meta.db_table

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    for field_name in field_names:
        field = model._meta.get_field(field_name)
        if field.column in existing_columns:
            continue
        schema_editor.add_field(model, field)
        existing_columns.add(field.column)


def repair_legacy_core_columns(apps, schema_editor):
    for model_name, field_names in LEGACY_MODEL_FIELDS.items():
        model = apps.get_model("core", model_name)
        add_missing_columns(model, field_names, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_repair_legacy_appuser_columns"),
    ]

    operations = [
        migrations.RunPython(
            repair_legacy_core_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
