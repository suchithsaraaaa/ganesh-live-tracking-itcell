"""
Django Management Command to geocode Idol installation addresses into geographic coordinates.
Enforces data integrity, privacy sanitization, and structured status tracking (GEOCODED, PARTIAL, UNRESOLVED).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.idols.models import Idol, GeocodingStatus
from apps.idols.services.geocoding import geocode_idol, get_geocoder


class Command(BaseCommand):
    help = 'Geocode eligible (>=15ft) Ganesh Idols into persistent geographic coordinates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of eligible records to geocode (e.g. 10, 50)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-geocode records even if they already have coordinates'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform geocoding queries without saving coordinates to the database'
        )
        parser.add_argument(
            '--provider',
            type=str,
            default=None,
            help='Geocoding provider override (e.g. mock, nominatim)'
        )
        parser.add_argument(
            '--all-heights',
            action='store_true',
            help='Include all idols rather than strictly operational eligible (>=15ft) idols'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        dry_run = options['dry_run']
        all_heights = options['all_heights']
        provider_override = options.get('provider')


        self.stdout.write(self.style.MIGRATE_HEADING("=== Hyderabad Police Ganesh Visarjan: Idol Geocoding Pipeline ==="))

        qs = Idol.objects.all().order_by('id')
        if not all_heights:
            qs = qs.filter(idol_height__gte=15.0)

        total_eligible = qs.count()
        self.stdout.write(f"Total operational target population: {total_eligible}")

        if not force:
            qs = qs.filter(latitude__isnull=True)
            self.stdout.write(f"Ungeocoded pending records: {qs.count()}")
        else:
            self.stdout.write(self.style.WARNING("Force mode enabled: reprocessing all targeted records."))

        if limit:
            qs = qs[:limit]
            self.stdout.write(self.style.WARNING(f"Batch limited to first {limit} records for controlled processing."))

        target_records = list(qs)
        if not target_records:
            self.stdout.write(self.style.SUCCESS("All targeted idols are already geocoded. Nothing to do."))
            return

        geocoder = get_geocoder(provider=provider_override)
        self.stdout.write(f"Active Geocoding Provider: {geocoder.__class__.__name__}")
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN MODE]: Database updates will NOT be committed."))

        geocoded_count = 0
        partial_count = 0
        unresolved_count = 0
        failed_samples = []

        now = timezone.now()

        for idx, idol in enumerate(target_records, start=1):
            res = geocode_idol(idol, geocoder=geocoder)
            lat = res['latitude']
            lon = res['longitude']
            status = res['status']
            confidence = res['confidence']

            if status == GeocodingStatus.GEOCODED:
                geocoded_count += 1
                symbol = self.style.SUCCESS("[GEOCODED]")
            elif status == GeocodingStatus.PARTIAL:
                partial_count += 1
                symbol = self.style.WARNING("[PARTIAL]")
            else:
                unresolved_count += 1
                symbol = self.style.ERROR("[UNRESOLVED]")
                if len(failed_samples) < 5:
                    failed_samples.append((idol.gpid, idol.address, idol.police_station))

            self.stdout.write(
                f"[{idx}/{len(target_records)}] {idol.gpid} (H: {idol.idol_height}ft) {symbol} "
                f"-> ({lat}, {lon}) [{confidence}] | PS: {idol.police_station}"
            )

            if not dry_run:
                idol.latitude = lat
                idol.longitude = lon
                idol.geocoding_status = status
                idol.geocoding_confidence = confidence
                idol.geocoding_provider = res.get('provider', '')
                idol.geocoded_at = now
                idol.save(update_fields=[
                    'latitude', 'longitude', 'geocoding_status',
                    'geocoding_confidence', 'geocoding_provider', 'geocoded_at'
                ])

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.MIGRATE_HEADING("=== Geocoding Reconciliation Summary ==="))
        self.stdout.write(f"Total Processed in this run: {len(target_records)}")
        self.stdout.write(f"High-Confidence Geocoded:    {geocoded_count}")
        self.stdout.write(f"Partial (Locality) Geocoded: {partial_count}")
        self.stdout.write(f"Unresolved:                  {unresolved_count}")
        if failed_samples:
            self.stdout.write("\nSample Unresolved Records:")
            for gpid, addr, ps in failed_samples:
                self.stdout.write(f"  - GPID: {gpid} | PS: {ps} | Addr: '{addr}'")
        self.stdout.write("=" * 60)
