from django.db import migrations


APPUSER_LEGACY_FIELDS = [
    "full_name",
    "mobile_number",
    "date_of_birth",
    "profile_photo_url",
    "location",
    "state",
    "address",
    "is_verified",
    "is_frozen",
    "frozen_until",
    "is_pending_deletion",
    "deletion_scheduled_at",
]


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


def repair_legacy_appuser_columns(apps, schema_editor):
    app_user = apps.get_model("core", "AppUser")
    add_missing_columns(app_user, APPUSER_LEGACY_FIELDS, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_tutorprofile_first_lesson_free"),
    ]

    operations = [
        migrations.RunPython(
            repair_legacy_appuser_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
