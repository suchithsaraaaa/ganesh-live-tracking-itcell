"""
Django Management Command to import the master Hyderabad Ganesh Idol dataset.
Safely processes authoritative GPIDs without regeneration, captures invalid
or duplicate rows into structured ImportIssue records, and produces summary statistics.
"""
import os
import re
from datetime import datetime
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.idols.models import Idol, ImportRun, ImportIssue, ImportIssueType


def clean_val(val):
    if val is None or pd.isna(val):
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none', 'null') else s


def parse_date_val(val):
    if val is None or pd.isna(val):
        return None
    try:
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        dt = pd.to_datetime(val, errors='coerce')
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return None


def parse_decimal_val(val):
    if val is None or pd.isna(val):
        return None
    try:
        s = str(val).strip()
        # Strip units like 'ft', 'feet', 'inch' if any
        s = re.sub(r'[^\d.]', '', s)
        if s:
            return round(float(s), 2)
    except Exception:
        pass
    return None


class Command(BaseCommand):
    help = 'Import authoritative Ganesh Idol master dataset from XLS/XLSX file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            default='data/HYDERABAD_Data (15).xls',
            help='Path to the authoritative idol master dataset (XLS/XLSX)'
        )
        parser.add_argument(
            '--reference',
            default='data/UNIQUE-CODE-FINAL-LIST.xlsx',
            help='Path to the 72 PS reference workbook'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='[Development Only] Limit the number of records to process for quick testing'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for database bulk operations'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        ref_path = options['reference']
        limit = options['limit']
        batch_size = options['batch_size']

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"Data file not found at: {file_path}"))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"Starting Idol Master Data Import from: {file_path}"))
        if limit:
            self.stdout.write(self.style.WARNING(f"[DEV ONLY] Processing limited to first {limit} records."))

        # 1. Load 72 PS Reference mappings
        ps_ref_map = {}
        if os.path.exists(ref_path):
            try:
                ref_df = pd.read_excel(ref_path, sheet_name='72 PS First Unique IDs')
                for _, r in ref_df.iterrows():
                    ps_name = clean_val(r.get('ps_name')).lower()
                    if ps_name:
                        ps_ref_map[ps_name] = {
                            'ps_code': clean_val(r.get('ps_code')),
                            'zone_code': clean_val(r.get('ZONE CODE')),
                            'zone_name': clean_val(r.get('dcp_zone_name')),
                            'acp_div': clean_val(r.get('acp_div_name')),
                            'first_uid': clean_val(r.get('First Unique-id')),
                        }
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(ps_ref_map)} police station mappings from reference workbook."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not load reference workbook: {e}"))

        # 2. Read Source Dataset
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read source file: {e}"))
            return

        total_rows = len(df)
        if limit:
            df = df.head(limit)
            total_rows = len(df)

        import_run = ImportRun.objects.create(
            file_name=os.path.basename(file_path),
            total_rows=total_rows,
            summary_notes="Execution started"
        )

        seen_gpids = {}
        idols_to_create = []
        issues_to_create = []

        imported_count = 0
        skipped_count = 0
        invalid_gpid_count = 0
        duplicate_gpid_count = 0
        invalid_ps_count = 0

        # Existing GPIDs in database for update vs insert detection
        existing_gpids = set(Idol.objects.values_list('gpid', flat=True))
        updated_count = 0

        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel 1-based index including header
            raw_gpid = clean_val(row.get('GPID'))
            ref_no = clean_val(row.get('Ref No'))
            ps_name = clean_val(row.get('Ps Name'))

            raw_row_data = {str(k): clean_val(v) for k, v in row.items()}

            # A. Check Missing GPID
            if not raw_gpid:
                skipped_count += 1
                invalid_gpid_count += 1
                issues_to_create.append(ImportIssue(
                    import_run=import_run,
                    row_number=row_num,
                    gpid='',
                    ref_no=ref_no,
                    ps_name=ps_name,
                    issue_type=ImportIssueType.MISSING_GPID,
                    error_message='Source record has no GPID.',
                    raw_row_data=raw_row_data
                ))
                continue

            # B. Check Duplicate GPID in this run
            if raw_gpid in seen_gpids:
                prev_row = seen_gpids[raw_gpid]
                skipped_count += 1
                duplicate_gpid_count += 1
                issues_to_create.append(ImportIssue(
                    import_run=import_run,
                    row_number=row_num,
                    gpid=raw_gpid,
                    ref_no=ref_no,
                    ps_name=ps_name,
                    issue_type=ImportIssueType.DUPLICATE_GPID,
                    error_message=f'Duplicate GPID in source dataset (previously seen at row {prev_row}).',
                    raw_row_data=raw_row_data
                ))
                continue

            # C. Check PS mapping and code
            PS_NAME_ALIASES = {
                'langer house': 'langar house',
                'rein bazar': 'reinbazar',
                'medipatnam': 'mehdipatnam',
                'bhavani nagar': 'bhavaninagar',
            }
            norm_ps = ps_name.lower()
            norm_ps = PS_NAME_ALIASES.get(norm_ps, norm_ps)
            ps_code = ''
            ps_lookup = ps_ref_map.get(norm_ps)
            if ps_lookup:
                ps_code = ps_lookup['ps_code']
            else:
                invalid_ps_count += 1

            seen_gpids[raw_gpid] = row_num

            # Check if this GPID already exists in DB
            is_update = raw_gpid in existing_gpids

            # Build operational Idol instance
            idol_instance = Idol(
                gpid=raw_gpid,
                ref_no=ref_no,
                name=clean_val(row.get('Name')),
                association_name=clean_val(row.get('Association Name')),
                dist_name=clean_val(row.get('Dist Name')) or 'HYDERABAD',
                zone=clean_val(row.get('Dcp Zone Name')),
                division=clean_val(row.get('Acp Div Name')),
                police_station=ps_name,
                ps_code=ps_code,
                address=clean_val(row.get('Address')),
                instal_h_no=clean_val(row.get('Instal_h_no')),
                instal_street=clean_val(row.get('Snstal_street')),
                instal_floor=clean_val(row.get('Instal_floor')),
                instal_village=clean_val(row.get('Instal_village')),
                instal_pin=clean_val(row.get('Instal_pin')),
                idol_height=parse_decimal_val(row.get('Idol Height')),
                pandal_height=parse_decimal_val(row.get('Pendal Height')),
                immersion_date=parse_date_val(row.get('Immerse Date')),
                river_name=clean_val(row.get('River Name')),
                lake_type=clean_val(row.get('Lake Type')),
                idol_type=clean_val(row.get('Idol Type')),
                specify_type=clean_val(row.get('Specify Type')),
                idol_area_type=clean_val(row.get('Idol Area Type')),
                instal_from_date=parse_date_val(row.get('Instal From Date')),
                instal_to_date=parse_date_val(row.get('Instal To Date')),
                status=clean_val(row.get('Status')) or 'APPROVED',
                raw_metadata={
                    'mobile_no': clean_val(row.get('Mobile No')),
                    'email': clean_val(row.get('Email')),
                    'member1': clean_val(row.get('Member1')),
                    'mob_member1': clean_val(row.get('Mob_Member1')),
                    'member2': clean_val(row.get('Member2')),
                    'mob_member2': clean_val(row.get('Mob Member2')),
                    'member3': clean_val(row.get('Member3')),
                    'mob_member3': clean_val(row.get('Mob Member3')),
                    'member4': clean_val(row.get('Member4')),
                    'mob_member4': clean_val(row.get('Mob Member4')),
                    'member5': clean_val(row.get('Member5')),
                    'mob_member5': clean_val(row.get('Mob Member5')),
                    'owner_consent': clean_val(row.get('Owner Consent')),
                    'tranco_consent': clean_val(row.get('Tranco Consent')),
                    'loud_speaker': clean_val(row.get('Loud Speaker')),
                    'cultural_program': clean_val(row.get('Cultural Program')),
                    'cc_cam_count': clean_val(row.get('CC Cam Count')),
                }
            )

            idols_to_create.append(idol_instance)
            if is_update:
                updated_count += 1
            else:
                imported_count += 1

            # Batch flush
            if len(idols_to_create) >= batch_size:
                with transaction.atomic():
                    Idol.objects.bulk_create(
                        idols_to_create,
                        update_conflicts=True,
                        update_fields=[
                            'ref_no', 'name', 'association_name', 'dist_name', 'zone', 'division',
                            'police_station', 'ps_code', 'address', 'instal_h_no', 'instal_street',
                            'instal_floor', 'instal_village', 'instal_pin', 'idol_height',
                            'pandal_height', 'immersion_date', 'river_name', 'lake_type',
                            'idol_type', 'specify_type', 'idol_area_type', 'instal_from_date',
                            'instal_to_date', 'status', 'raw_metadata'
                        ],
                        unique_fields=['gpid']
                    )
                idols_to_create.clear()

            if len(issues_to_create) >= batch_size:
                with transaction.atomic():
                    ImportIssue.objects.bulk_create(issues_to_create)
                issues_to_create.clear()

        # Final flush
        if idols_to_create:
            with transaction.atomic():
                Idol.objects.bulk_create(
                    idols_to_create,
                    update_conflicts=True,
                    update_fields=[
                        'ref_no', 'name', 'association_name', 'dist_name', 'zone', 'division',
                        'police_station', 'ps_code', 'address', 'instal_h_no', 'instal_street',
                        'instal_floor', 'instal_village', 'instal_pin', 'idol_height',
                        'pandal_height', 'immersion_date', 'river_name', 'lake_type',
                        'idol_type', 'specify_type', 'idol_area_type', 'instal_from_date',
                        'instal_to_date', 'status', 'raw_metadata'
                    ],
                    unique_fields=['gpid']
                )

        if issues_to_create:
            with transaction.atomic():
                ImportIssue.objects.bulk_create(issues_to_create)

        # Update ImportRun summary
        import_run.completed_at = timezone.now()
        import_run.imported_count = imported_count
        import_run.updated_count = updated_count
        import_run.skipped_count = skipped_count
        import_run.invalid_gpid_count = invalid_gpid_count
        import_run.duplicate_gpid_count = duplicate_gpid_count
        import_run.invalid_ps_count = invalid_ps_count
        import_run.summary_notes = f"Completed successfully. Imported: {imported_count}, Skipped: {skipped_count}"
        import_run.save()

        # Final Report matching exact specification
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("IMPORT SUMMARY"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"Records read: {total_rows}")
        self.stdout.write(f"Imported: {imported_count}")
        self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Invalid GPIDs: {invalid_gpid_count}")
        self.stdout.write(f"Duplicate GPIDs: {duplicate_gpid_count}")
        self.stdout.write(f"Invalid PS mappings: {invalid_ps_count}")
        self.stdout.write("=" * 50)
