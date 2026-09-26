"""
Management command to precompute and cache place names and local police station jurisdictions
for all report-eligible idols.
Ensures zero external network calls during subsequent PDF generation and report downloads.

Usage:
    python manage.py precompute_report_locations --all
    python manage.py precompute_report_locations --gpid HYDCMRZDBPR1182
    python manage.py precompute_report_locations --limit 10
"""
import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.idols.models import Idol
from apps.tracking.models import TrackingSession, LocationPoint, IdolEvent
from apps.geography.models import BoundaryEvent, GeocodingCache
from apps.geography.services import get_bucket, get_or_create_location_enrichment
from apps.reports.services import get_report_eligible_q


class Command(BaseCommand):
    help = 'Precomputes and caches reverse-geocoded place names and PS jurisdiction for report-eligible idols.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Process all report-eligible idols.')
        parser.add_argument('--gpid', type=str, help='Process a specific GPID.')
        parser.add_argument('--limit', type=int, default=None, help='Limit number of idols to process.')
        parser.add_argument('--delay', type=float, default=1.1, help='Rate limit delay between external geocoding requests (default 1.1s).')

    def handle(self, *args, **options):
        gpid = options.get('gpid')
        limit = options.get('limit')
        delay = options.get('delay', 1.1)

        if gpid:
            idols = list(Idol.objects.filter(gpid__iexact=gpid))
            if not idols:
                self.stderr.write(self.style.ERROR(f"No idol found with GPID {gpid}"))
                return
            self.stdout.write(f"Target GPID: {gpid}")
        else:
            eligible_q = get_report_eligible_q()
            qs = Idol.objects.filter(eligible_q).distinct().order_by('-updated_at')
            if limit:
                qs = qs[:limit]
            idols = list(qs)

        total_idols = len(idols)
        self.stdout.write(self.style.SUCCESS(f"Found {total_idols} report-eligible idol(s) to process."))

        # 1. Harvest all timeline coordinates
        unique_buckets = {}  # (lat_b, lon_b) -> (lat, lon)
        total_timeline_points = 0

        for idx, idol in enumerate(idols, 1):
            session = TrackingSession.objects.filter(
                assignment__idol=idol
            ).order_by('-started_at').first()

            pts = []
            if session:
                pts = list(LocationPoint.objects.filter(session=session).order_by('recorded_at'))
                events = list(IdolEvent.objects.filter(
                    Q(tracking_session=session) | Q(idol=idol, tracking_session__isnull=True)
                ))
            else:
                pts = list(LocationPoint.objects.filter(session__assignment__idol=idol).order_by('recorded_at'))
                events = list(IdolEvent.objects.filter(idol=idol))

            boundary_events = list(BoundaryEvent.objects.filter(idol=idol))

            # Sample points exactly as the PDF report timeline does
            sampled_coords = []
            if pts:
                sampled_coords.append((pts[0].latitude, pts[0].longitude))
                if len(pts) > 2:
                    last_time = pts[0].recorded_at
                    for pt in pts[1:-1]:
                        if (pt.recorded_at - last_time).total_seconds() >= 720.0:  # 12 mins
                            sampled_coords.append((pt.latitude, pt.longitude))
                            last_time = pt.recorded_at
                if len(pts) > 1:
                    sampled_coords.append((pts[-1].latitude, pts[-1].longitude))

            for ev in events:
                if ev.latitude and ev.longitude:
                    sampled_coords.append((ev.latitude, ev.longitude))

            for be in boundary_events:
                if be.latitude and be.longitude:
                    sampled_coords.append((be.latitude, be.longitude))

            total_timeline_points += len(sampled_coords)
            for lat, lon in sampled_coords:
                b = get_bucket(lat, lon)
                if b not in unique_buckets:
                    unique_buckets[b] = (lat, lon)

        self.stdout.write(f"Harvested {total_timeline_points} timeline coordinates across {len(unique_buckets)} unique coordinate bucket(s).")

        # 2. Check existing cache
        existing_buckets = set(
            GeocodingCache.objects.values_list('lat_bucket', 'lon_bucket')
        )
        missing_buckets = {b: coords for b, coords in unique_buckets.items() if b not in existing_buckets}

        cached_reused = len(unique_buckets) - len(missing_buckets)
        self.stdout.write(self.style.SUCCESS(f"Reusing {cached_reused} already cached bucket(s). Need to resolve {len(missing_buckets)} new bucket(s)."))

        newly_resolved = 0
        unresolved_count = 0

        if not missing_buckets:
            self.stdout.write(self.style.SUCCESS("All required location buckets are already cached!"))
        else:
            for i, (b, (lat, lon)) in enumerate(missing_buckets.items(), 1):
                try:
                    place_name, ps_name, zone, div = get_or_create_location_enrichment(lat, lon, allow_network=True)
                    if place_name == 'Location unavailable':
                        unresolved_count += 1
                    else:
                        newly_resolved += 1
                    if i % 10 == 0 or i == len(missing_buckets):
                        self.stdout.write(f"[{i}/{len(missing_buckets)}] ({lat:.5f}, {lon:.5f}) -> {place_name} [{ps_name}]")
                except Exception as e:
                    self.stderr.write(f"Error resolving ({lat}, {lon}): {e}")
                    unresolved_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n=== PRECOMPUTATION SUMMARY ===\n"
            f"Eligible Idols Scanned: {total_idols}\n"
            f"Total Timeline Coordinates: {total_timeline_points}\n"
            f"Unique Coordinate Buckets: {len(unique_buckets)}\n"
            f"Cached Buckets Reused: {cached_reused}\n"
            f"Newly Enriched Buckets: {newly_resolved}\n"
            f"Unresolved / Failed Buckets: {unresolved_count}\n"
            f"================================"
        ))
