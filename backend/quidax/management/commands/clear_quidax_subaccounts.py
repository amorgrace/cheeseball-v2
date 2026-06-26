import logging

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Clears all stale QuidaxSubAccount and QuidaxWalletAddress records from "
        "the database. Use this when switching to a new Quidax merchant account "
        "so all users get fresh sub-accounts generated on their next deposit/trade."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many records would be deleted without actually deleting them.",
        )

    def handle(self, *args, **options):
        from quidax.models import QuidaxSubAccount, QuidaxWalletAddress

        dry_run = options["dry_run"]

        sub_count = QuidaxSubAccount.objects.count()
        wallet_count = QuidaxWalletAddress.objects.count()

        self.stdout.write(f"Found {sub_count} sub-account(s) and {wallet_count} wallet address(es).")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no records deleted."))
            return

        with transaction.atomic():
            # Wallet addresses reference sub-accounts, so delete them first
            w_deleted, _ = QuidaxWalletAddress.objects.all().delete()
            s_deleted, _ = QuidaxSubAccount.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {w_deleted} wallet address(es) and {s_deleted} sub-account(s). "
                "They will be recreated fresh on the next user request."
            )
        )
