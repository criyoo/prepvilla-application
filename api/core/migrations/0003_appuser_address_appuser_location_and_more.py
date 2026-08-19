import uuid
from django.db import migrations, models


def drop_favorite_tutor_table_if_present(apps, schema_editor):
    table_name = "core_favoritetutor"

    if table_name not in schema_editor.connection.introspection.table_names():
        return

    favorite_tutor = apps.get_model("core", "FavoriteTutor")
    schema_editor.delete_model(favorite_tutor)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_student_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='appuser',
            name='address',
            field=models.TextField(blank=True, default='', help_text='Student full address'),
        ),
        migrations.AddField(
            model_name='appuser',
            name='location',
            field=models.CharField(blank=True, default='', help_text='Student location/city', max_length=100),
        ),
        migrations.AddField(
            model_name='appuser',
            name='profile_photo_url',
            field=models.URLField(blank=True, default='', help_text='Profile photo URL for students'),
        ),
        migrations.AddField(
            model_name='appuser',
            name='state',
            field=models.CharField(blank=True, default='', help_text='Student state/province', max_length=100),
        ),
        migrations.AlterField(
            model_name='mobilenumberchangerequest',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='studentverificationrequest',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    drop_favorite_tutor_table_if_present,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(
                    name='FavoriteTutor',
                ),
            ],
        ),
    ]
