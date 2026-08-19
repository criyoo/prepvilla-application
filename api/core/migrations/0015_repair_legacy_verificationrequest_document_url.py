from django.db import migrations


def repair_verificationrequest_document_url(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "core_verificationrequest"

    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }

    if "document_url" not in existing_columns:
        return

    quoted_table = schema_editor.quote_name(table_name)
    quoted_document_url = schema_editor.quote_name("document_url")
    quoted_document_urls = schema_editor.quote_name("document_urls")

    if "document_urls" in existing_columns:
        schema_editor.execute(
            f"""
            UPDATE {quoted_table}
            SET {quoted_document_urls} = {quoted_document_url}
            WHERE ({quoted_document_urls} IS NULL OR {quoted_document_urls} = '')
              AND {quoted_document_url} IS NOT NULL
              AND {quoted_document_url} <> ''
            """
        )

    schema_editor.execute(
        f"ALTER TABLE {quoted_table} DROP COLUMN {quoted_document_url}"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_repair_legacy_core_columns"),
    ]

    operations = [
        migrations.RunPython(
            repair_verificationrequest_document_url,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
