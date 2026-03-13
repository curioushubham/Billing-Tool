from django.core.management.base import BaseCommand
from invoices.services import process_reminders


class Command(BaseCommand):
    help = 'Send invoice payment reminder emails (run daily via cron/Task Scheduler)'

    def handle(self, *args, **options):
        self.stdout.write('Processing reminder emails...')
        results = process_reminders()
        self.stdout.write(self.style.SUCCESS(
            f"Sent {results['upcoming']} upcoming, {results['due']} due, {results['overdue']} overdue reminders."
        ))
