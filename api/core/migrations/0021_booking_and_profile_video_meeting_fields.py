from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_alter_verificationrequest_profile_photo_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="video_meeting_space",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="booking",
            name="video_meeting_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="video_meeting_space",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="video_meeting_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
