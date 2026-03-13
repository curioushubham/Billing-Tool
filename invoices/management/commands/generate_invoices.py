from datetime import date
from django.core.management.base import BaseCommand
from invoices.services import generate_monthly_invoices


class Command(BaseCommand):
    help = 'Generate monthly invoices for all active tenants'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year)
        parser.add_argument('--month', type=int, default=date.today().month)

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        self.stdout.write(f'Generating invoices for {year}-{month:02d}...')

        created, skipped = generate_monthly_invoices(year, month)

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(created)} invoices, skipped {len(skipped)} (already exist).'
        ))
