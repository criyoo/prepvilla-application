from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_booking_and_profile_video_meeting_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="availabilityslot",
            index=models.Index(fields=["tutor_profile", "starts_at"], name="core_slot_tutor_start_idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["student_user", "created_at"], name="core_book_student_ct_idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["tutor_profile", "created_at"], name="core_booking_tutor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["status", "created_at"], name="core_book_status_ct_idx"),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["student_user", "created_at"], name="core_conv_student_created_idx"),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["tutor_profile", "created_at"], name="core_conv_tutor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="favoritetutor",
            index=models.Index(fields=["student_user", "created_at"], name="core_fav_student_created_idx"),
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["tutor_profile", "created_at"], name="core_review_tutor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorprofile",
            index=models.Index(fields=["is_listed", "verification_status"], name="core_tutor_listed_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorprofile",
            index=models.Index(fields=["home_state", "home_city"], name="core_tutor_state_city_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorprofile",
            index=models.Index(fields=["hourly_rate_cents"], name="core_tutor_rate_idx"),
        ),
        migrations.AddIndex(
            model_name="tutorprofile",
            index=models.Index(fields=["gender"], name="core_tutor_gender_idx"),
        ),
    ]
