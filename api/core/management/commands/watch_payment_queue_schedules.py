from django.core.management.base import BaseCommand

from core.payment_queue import watch_scheduled_payment_tasks


class Command(BaseCommand):
    help = "Enqueue scheduled payment jobs for Docker Compose/RQ environments."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Enqueue due scheduled jobs once and exit.")

    def handle(self, *args, **options):
        watch_scheduled_payment_tasks(once=bool(options["once"]))
