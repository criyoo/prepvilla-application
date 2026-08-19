from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_tutor_profile_delivery_and_documents"),
    ]

    operations = [
        migrations.AlterField(
            model_name="verificationrequest",
            name="profile_photo_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
