# Generated manually for the new student models

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MobileNumberChangeRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('current_mobile', models.CharField(blank=True, default='', max_length=20)),
                ('requested_mobile', models.CharField(max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('admin_notes', models.TextField(blank=True, default='')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_mobile_changes', to='core.appuser')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mobile_change_requests', to='core.appuser')),
            ],
        ),
        migrations.CreateModel(
            name='StudentVerificationRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('profile_photo_url', models.URLField(help_text='Student profile photo URL')),
                ('date_of_birth', models.DateField(help_text='Student date of birth')),
                ('mobile_number', models.CharField(help_text='Student mobile number', max_length=20)),
                ('location', models.CharField(help_text='Student location/city', max_length=100)),
                ('state', models.CharField(help_text='Student state/province', max_length=100)),
                ('address', models.TextField(help_text='Student full address')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('admin_notes', models.TextField(blank=True, default='')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_student_verifications', to='core.appuser')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='student_verification', to='core.appuser')),
            ],
        ),
    ]
