import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from core.payment_queue import enqueue_ready_payouts


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Periodically enqueue completed lesson payouts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=getattr(settings, "FLUTTERWAVE_PAYOUT_RELEASE_WATCH_INTERVAL_SECONDS", 300),
            help="Seconds to wait between payout checks.",
        )

    def handle(self, *args, **options):
        interval = max(int(options["interval"]), 60)
        while True:
            try:
                enqueue_ready_payouts(source="watch_ready_payouts")
            except Exception:
                logger.exception("Ready payout queue iteration failed.")
            time.sleep(interval)
