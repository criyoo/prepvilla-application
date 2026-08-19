from django.core.management.base import BaseCommand

from core.seed_demo_data import seed_demo_accounts_students, seed_demo_accounts_tutors


class Command(BaseCommand):
    help = "Synchronize the default demo tutor and student accounts when enabled."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run demo account seeding even when SEED_DEMO_ACCOUNTS is disabled (except production).",
        )

    def handle(self, *args, **options):
        force = bool(options["force"])
        tutor_result = seed_demo_accounts_tutors(force=force)
        student_result = seed_demo_accounts_students(force=force)
        self.stdout.write(f"Tutor demo accounts: {tutor_result}")
        self.stdout.write(f"Student demo accounts: {student_result}")
