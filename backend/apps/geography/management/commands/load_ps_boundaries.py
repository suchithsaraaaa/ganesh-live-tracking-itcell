import os
import pandas as pd
from django.core.management.base import BaseCommand
from apps.geography.models import PoliceStationBoundary


class Command(BaseCommand):
    help = 'Populate 72 Police Station reference data from UNIQUE-CODE-FINAL-LIST.xlsx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/UNIQUE-CODE-FINAL-LIST.xlsx',
            help='Path to UNIQUE-CODE-FINAL-LIST.xlsx'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        if not os.path.exists(file_path):
            self.stderr.write(f"File not found: {file_path}")
            return

        df = pd.read_excel(file_path, sheet_name='72 PS First Unique IDs')
        created_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            ps_name = str(row.get('ps_name', '')).strip()
            if not ps_name:
                continue

            ps_code = str(row.get('ps_code', '')).strip()
            zone = str(row.get('dcp_zone_name', '')).strip()
            division = str(row.get('acp_div_name', '')).strip()
            first_uid = str(row.get('First Unique-id', '')).strip()

            start_num_raw = row.get('Code number starts from ')
            start_num = None
            try:
                if pd.notna(start_num_raw):
                    start_num = int(start_num_raw)
            except Exception:
                pass

            obj, created = PoliceStationBoundary.objects.update_or_create(
                ps_name=ps_name,
                defaults={
                    'ps_code': ps_code,
                    'zone': zone,
                    'division': division,
                    'first_unique_id': first_uid,
                    'starting_gpid_number': start_num,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully processed Police Stations: {created_count} created, {updated_count} updated."
        ))
