from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0030_tutor_bvn_numbers"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorprofile",
            name="country_of_birth",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="lga_of_origin",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
