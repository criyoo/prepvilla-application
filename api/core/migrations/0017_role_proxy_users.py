from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_repair_missing_legacy_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformAdminUser",
            fields=[],
            options={
                "verbose_name": "Platform admin",
                "verbose_name_plural": "Platform admins",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("core.appuser",),
        ),
        migrations.CreateModel(
            name="StudentUser",
            fields=[],
            options={
                "verbose_name": "Student",
                "verbose_name_plural": "Students",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("core.appuser",),
        ),
        migrations.CreateModel(
            name="TutorUser",
            fields=[],
            options={
                "verbose_name": "Tutor",
                "verbose_name_plural": "Tutors",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("core.appuser",),
        ),
    ]
