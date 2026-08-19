from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0033_support_request"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentverificationrequest",
            name="profile_photo_url",
            field=models.CharField(help_text="Student profile photo URL", max_length=500),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="bvn_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="country_of_birth",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="document_urls",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="lga_of_origin",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="qualification",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="studentverificationrequest",
            name="state_of_origin",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
