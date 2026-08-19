from django.core.management.base import BaseCommand, CommandError
from core.models import VerificationRequest, TutorProfile, AppUser

class Command(BaseCommand):
    help = 'Approve or reject tutor verification'

    def add_arguments(self, parser):
        parser.add_argument('tutor_id', type=str, help='Tutor ID (UUID)')
        parser.add_argument('action', choices=['approve', 'reject'], help='Action to take')
        parser.add_argument('--notes', type=str, default='', help='Notes for rejection')

    def handle(self, *args, **options):
        tutor_id = options['tutor_id']
        action = options['action']
        notes = options['notes']

        try:
            tp = TutorProfile.objects.get(id=tutor_id)
        except TutorProfile.DoesNotExist:
            raise CommandError(f'Tutor profile {tutor_id} not found')

        verification = VerificationRequest.objects.filter(tutor_profile=tp).first()
        if not verification:
            raise CommandError(f'No verification request found for tutor {tutor_id}')

        from django.utils import timezone
        verification.decided_at = timezone.now()

        if action == 'approve':
            verification.status = 'approved'
            tp.verification_status = 'approved'
            tp.save()
            self.stdout.write(self.style.SUCCESS(f'Verification approved for {tp.user.display_name}'))
        elif action == 'reject':
            verification.status = 'rejected'
            verification.notes = notes
            tp.verification_status = 'rejected'
            tp.is_listed = False
            tp.save(update_fields=['verification_status', 'is_listed'])
            self.stdout.write(self.style.SUCCESS(f'Verification rejected for {tp.user.display_name}'))

        verification.save()
