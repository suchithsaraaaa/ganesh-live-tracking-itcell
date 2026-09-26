import os
import json
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.geography.models import PoliceStationBoundary
from common.zones import normalize_ps_name, are_same_ps


class Command(BaseCommand):
    help = 'Populates 72 Police Stations and attaches authoritative boundary geometry from GeoJSON.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data/UNIQUE-CODE-FINAL-LIST.xlsx',
            help='Path to UNIQUE-CODE-FINAL-LIST.xlsx'
        )
        parser.add_argument(
            '--geojson',
            default=os.path.join(settings.BASE_DIR, 'apps', 'geography', 'data', 'hyderabad_ps_boundaries.geojson'),
            help='Path to Hyderabad PS boundaries GeoJSON'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and match without saving to database'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        geojson_path = options['geojson']
        dry_run = options.get('dry_run', False)

        # 1. Optionally load base metadata from Excel if requested and present
        if os.path.exists(file_path):
            self.stdout.write(f"Reading station metadata from {file_path}...")
            import pandas as pd
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

                if not dry_run:
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
                f"Base station records: {created_count} created, {updated_count} updated."
            ))

        # 2. Attach boundary polygons from GeoJSON
        if not os.path.exists(geojson_path):
            # Fallback to research location if apps/geography/data not yet built
            research_path = os.path.join(settings.BASE_DIR.parent, 'research', 'lawyerinsta', 'lawyerinsta_hyderabad_ps_boundaries.RESEARCH.geojson')
            if os.path.exists(research_path):
                geojson_path = research_path
            else:
                self.stderr.write(f"GeoJSON boundary file not found at {geojson_path}")
                return

        self.stdout.write(f"Loading boundary geometry from {geojson_path}...")
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        features = data.get('features', [])
        hyd_features = [f for f in features if f.get('properties', {}).get('commissionerate') == 'Hyderabad Commissionerate']

        self.stdout.write(f"Found {len(hyd_features)} Hyderabad Commissionerate feature(s) in GeoJSON.")

        from shapely.geometry import shape, mapping
        from shapely.validation import make_valid

        # Pre-index existing authoritative 72 stations
        existing_stations = list(PoliceStationBoundary.objects.all())
        station_by_name = {ps.ps_name.lower(): ps for ps in existing_stations}

        attached_count = 0
        no_geom_count = 0
        skipped_count = 0

        for feat in hyd_features:
            props = feat.get('properties', {})
            geom_data = feat.get('geometry')
            source_name = props.get('name', '')
            matched_ps_name = props.get('our_ps_name')

            # Find matching station in our 72 authoritative list
            target_ps = None
            if matched_ps_name and matched_ps_name.lower() in station_by_name:
                target_ps = station_by_name[matched_ps_name.lower()]
            else:
                # Try canonical matching
                for ps in existing_stations:
                    if are_same_ps(ps.ps_name, matched_ps_name or source_name):
                        target_ps = ps
                        break

            if not target_ps:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"Skipping non-registry station: {source_name}"))
                continue

            if not geom_data:
                no_geom_count += 1
                continue

            # Validate geometry coordinates [lon, lat] in Hyderabad bounding box
            g = shape(geom_data)
            if not g.is_valid:
                g = make_valid(g)

            # Ensure coordinates are within reasonable Hyderabad bounding box (17-18 N, 78-79 E)
            bounds = g.bounds  # (minx, miny, maxx, maxy) = (minlon, minlat, maxlon, maxlat)
            if not (78.0 <= bounds[0] <= 79.0 and 17.0 <= bounds[1] <= 18.0):
                self.stderr.write(f"Coordinates outside Hyderabad bounds for {target_ps.ps_name}: {bounds}")
                continue

            # If PostGIS is active, attach GEOSGeometry
            if getattr(settings, 'USE_POSTGIS', False) and not dry_run:
                try:
                    from django.contrib.gis.geos import GEOSGeometry
                    # Cleaned GeoJSON geometry
                    cleaned_geojson = json.dumps(mapping(g))
                    geos_geom = GEOSGeometry(cleaned_geojson, srid=4326)
                    target_ps.boundary = geos_geom
                    target_ps.save(update_fields=['boundary', 'updated_at'])
                    attached_count += 1
                except Exception as e:
                    self.stderr.write(f"Error attaching boundary to {target_ps.ps_name}: {e}")
            else:
                attached_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n=== BOUNDARY ATTACHMENT SUMMARY ===\n"
            f"Authoritative Registry Stations: {len(existing_stations)}\n"
            f"Hyderabad GeoJSON Features: {len(hyd_features)}\n"
            f"Boundaries Attached: {attached_count}\n"
            f"Stations Without Geometry: {no_geom_count}\n"
            f"Non-Registry Features Skipped: {skipped_count}\n"
            f"Dry Run: {dry_run}\n"
            f"===================================="
        ))
