"""
Authoritative Location and Police Station Jurisdiction Resolution Service.
Provides:
1. Local PostGIS point-in-polygon spatial lookup against PoliceStationBoundary.
2. Persistent normalized coordinate caching (GeocodingCache) at ~11m resolution.
3. Polite rate-limited reverse geocoding via Nominatim.
4. Non-blocking asynchronous enrichment for tracking sessions and report generation.
"""
import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db import IntegrityError, models, transaction

from apps.geography.models import GeocodingCache, PoliceStationBoundary
from common.zones import normalize_ps_name, normalize_zone

logger = logging.getLogger(__name__)

# Thread-safe rate limiter for external geocoder calls
_nominatim_lock = threading.Lock()
_last_nominatim_call = 0.0
NOMINATIM_USER_AGENT = "HyderabadPoliceGaneshTracking/1.0 (itcell@tspolice.gov.in)"

# In-flight deduplication set to prevent parallel requests for the same bucket
_in_flight_lock = threading.Lock()
_in_flight_buckets = set()


def get_bucket(lat: float, lon: float) -> Tuple[Decimal, Decimal]:
    """
    Normalizes coordinates to a 4-decimal place bucket (~11.1 meters resolution).
    Returns (Decimal(lat_bucket), Decimal(lon_bucket)).
    """
    return (
        Decimal(f"{float(lat):.4f}"),
        Decimal(f"{float(lon):.4f}")
    )


def resolve_ps_jurisdiction(lat: float, lon: float) -> Tuple[str, str, str]:
    """
    Performs authoritative local point-in-polygon spatial query against PoliceStationBoundary.
    Returns (canonical_ps_name, canonical_zone, division).
    Invariants:
    - Must be deterministic point-in-polygon on authoritative boundary geometry.
    - If no containing polygon found, or boundary is unpopulated: ('Jurisdiction unavailable', '', '')
    - If coordinate lies on multiple ambiguous boundaries: ('Boundary / Ambiguous', '', '')
    - NEVER guess nearest police station.
    - NEVER string-match locality to police station.
    """
    if not lat or not lon:
        return ('Jurisdiction unavailable', '', '')

    if getattr(settings, 'USE_POSTGIS', False):
        try:
            from django.contrib.gis.geos import Point

            # GeoDjango Point: Point(x, y) = Point(longitude, latitude)
            pt = Point(float(lon), float(lat), srid=4326)
            matches = list(PoliceStationBoundary.objects.filter(
                boundary__isnull=False,
                boundary__contains=pt
            ))

            if len(matches) == 1:
                ps = matches[0]
                return (
                    normalize_ps_name(ps.ps_name),
                    normalize_zone(ps.zone) or '',
                    ps.division or ''
                )
            elif len(matches) > 1:
                names = {normalize_ps_name(m.ps_name) for m in matches}
                if len(names) == 1:
                    ps = matches[0]
                    return (
                        list(names)[0],
                        normalize_zone(ps.zone) or '',
                        ps.division or ''
                    )
                logger.warning(f"Ambiguous boundary match at ({lat}, {lon}): {[m.ps_name for m in matches]}")
                return ('Boundary / Ambiguous', '', '')
            else:
                return ('Jurisdiction unavailable', '', '')
        except Exception as e:
            logger.warning(f"PostGIS spatial query error for ({lat}, {lon}): {e}")
            return ('Jurisdiction unavailable', '', '')

    return ('Jurisdiction unavailable', '', '')


def extract_place_name(data: dict) -> str:
    """
    Extracts a concise, human-readable place name suitable for police operational reports.
    Prefers:
    1. Prominent landmark, tourism, or leisure destination (e.g. People's Plaza, Tank Bund, Charminar).
    2. Recognizable suburb or neighbourhood locality (e.g. Dabeerpura, Chanchalguda, Khairatabad).
    3. Major arterial road when landmark/suburb is missing.
    Falls back to 'Location unavailable' on failure.
    """
    if not data or not isinstance(data, dict):
        return 'Location unavailable'

    addr = data.get('address', {})
    if not isinstance(addr, dict):
        return 'Location unavailable'

    # 1. Named landmarks / tourism / leisure / heritage
    for key in ['leisure', 'tourism', 'historic', 'amenity']:
        val = addr.get(key)
        if val and isinstance(val, str):
            val_clean = val.strip()
            # Ignore generic utility points like ATMs or clinics
            if not any(w in val_clean.lower() for w in ['health', 'hospital', 'clinic', 'atm', 'bank', 'school', 'toilet', 'sub station']):
                sub = addr.get('suburb') or addr.get('neighbourhood')
                if sub and isinstance(sub, str) and sub.lower() not in val_clean.lower():
                    return f"{val_clean}, {sub.strip()}"
                return val_clean

    road = str(addr.get('road') or '').strip()
    suburb = str(addr.get('suburb') or '').strip()
    neighbourhood = str(addr.get('neighbourhood') or '').strip()

    # 2. Prominent plaza / road / margin
    is_major_road = any(w in road.lower() for w in ['plaza', 'necklace', 'tank bund', 'marg', 'expressway', 'highway', 'flyover'])
    if is_major_road:
        if suburb and suburb.lower() not in road.lower():
            return f"{road}, {suburb}"
        return road

    # 3. Locality / Suburb / Neighbourhood
    if neighbourhood and suburb and neighbourhood.lower() != suburb.lower():
        if len(neighbourhood) + len(suburb) < 30:
            return f"{neighbourhood}, {suburb}"
        return suburb
    if suburb:
        return suburb
    if neighbourhood:
        return neighbourhood
    if road:
        return road

    city = addr.get('city') or addr.get('town') or addr.get('county')
    if city and isinstance(city, str):
        return city.strip()

    return 'Location unavailable'


def reverse_geocode_photon(lat: float, lon: float) -> Tuple[str, dict]:
    """
    Fast, reliable reverse geocoding fallback using Photon (OSM-based).
    Returns (place_name, properties_dict).
    """
    try:
        url = f"https://photon.komoot.io/reverse?lat={float(lat):.5f}&lon={float(lon):.5f}"
        req = urllib.request.Request(url, headers={'User-Agent': NOMINATIM_USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            features = data.get('features', [])
            if features:
                props = features[0].get('properties', {})
                name = props.get('name') or props.get('street')
                locality = props.get('locality') or props.get('district') or props.get('city')
                if name and locality and name.lower() not in locality.lower():
                    place_name = f"{name}, {locality}"
                elif name:
                    place_name = name
                elif locality:
                    place_name = locality
                else:
                    place_name = 'Location unavailable'
                return (place_name, props)
    except Exception as e:
        logger.warning(f"Photon reverse geocode error for ({lat}, {lon}): {e}")
    return ('Location unavailable', {})


def reverse_geocode_nominatim(lat: float, lon: float, delay_sec: float = 1.1) -> Tuple[str, dict]:
    """
    Polite, rate-limited reverse geocoding via OpenStreetMap Nominatim with automatic Photon fallback.
    Thread-safe and adheres to 1 request/second policy.
    Returns (place_name, raw_address_dict).
    """
    global _last_nominatim_call

    with _nominatim_lock:
        elapsed = time.time() - _last_nominatim_call
        if elapsed < delay_sec:
            time.sleep(delay_sec - elapsed)

        params = urllib.parse.urlencode({
            'lat': f"{float(lat):.5f}",
            'lon': f"{float(lon):.5f}",
            'format': 'json',
            'addressdetails': 1
        })
        url = f"https://nominatim.openstreetmap.org/reverse?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': NOMINATIM_USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                _last_nominatim_call = time.time()
                data = json.loads(resp.read().decode('utf-8'))
                if isinstance(data, dict):
                    place_name = extract_place_name(data)
                    if place_name != 'Location unavailable':
                        return (place_name, data.get('address', {}))
        except Exception as e:
            _last_nominatim_call = time.time()
            logger.warning(f"Reverse geocode error for ({lat}, {lon}): {e}")

    # Fallback to Photon when Nominatim is rate-limited (429), unavailable, or returns unindexed
    photon_place, photon_props = reverse_geocode_photon(lat, lon)
    if photon_place != 'Location unavailable':
        return (photon_place, photon_props)

    return ('Location unavailable', {})


def get_or_create_location_enrichment(lat: float, lon: float, allow_network: bool = False) -> Tuple[str, str, str, str]:
    """
    Resolves place name and police station jurisdiction for a given coordinate.
    Returns (place_name, police_station, zone, division).

    When allow_network=False (e.g. during PDF generation):
    - Reads ONLY from local GeocodingCache.
    - If uncached: queries local PostGIS boundary (sub-millisecond, zero network) and returns ('Location unavailable', ps_name, zone, division).
    - NEVER triggers external HTTP geocoder during report download!

    When allow_network=True (background enrichment / management command):
    - If uncached: queries PostGIS + Nominatim/Photon and saves to GeocodingCache.
    """
    if not lat or not lon:
        return ('Location unavailable', 'Jurisdiction unavailable', '', '')

    lat_b, lon_b = get_bucket(lat, lon)

    # 1. Check local persistent cache
    cache_entry = GeocodingCache.objects.filter(lat_bucket=lat_b, lon_bucket=lon_b).first()
    if cache_entry:
        ps_name = cache_entry.police_station
        zone = cache_entry.zone
        division = cache_entry.division
        # Self-healing: if cached before boundaries were loaded, re-resolve via local PostGIS PIP
        if ps_name == 'Jurisdiction unavailable':
            res_ps, res_zone, res_div = resolve_ps_jurisdiction(lat, lon)
            if res_ps != 'Jurisdiction unavailable':
                ps_name, zone, division = res_ps, res_zone, res_div
        return (
            cache_entry.place_name,
            ps_name,
            zone,
            division
        )

    # 2. Local PS jurisdiction lookup (always fast, local PostGIS query)
    ps_name, zone, division = resolve_ps_jurisdiction(lat, lon)

    if not allow_network:
        # Zero external HTTP requests during PDF download path
        return ('Location unavailable', ps_name, zone, division)

    # 3. Network resolution with in-flight deduplication
    bucket_key = (lat_b, lon_b)
    with _in_flight_lock:
        if bucket_key in _in_flight_buckets:
            # Another thread is actively resolving this bucket; fallback to local
            return ('Location resolving...', ps_name, zone, division)
        _in_flight_buckets.add(bucket_key)

    try:
        place_name, raw_addr = reverse_geocode_nominatim(lat, lon)
        try:
            entry, _ = GeocodingCache.objects.update_or_create(
                lat_bucket=lat_b,
                lon_bucket=lon_b,
                defaults={
                    'place_name': place_name,
                    'police_station': ps_name,
                    'zone': zone,
                    'division': division,
                    'raw_address': raw_addr,
                }
            )
            return (entry.place_name, entry.police_station, entry.zone, entry.division)
        except IntegrityError:
            # Concurrently created by another process
            entry = GeocodingCache.objects.filter(lat_bucket=lat_b, lon_bucket=lon_b).first()
            if entry:
                return (entry.place_name, entry.police_station, entry.zone, entry.division)
            return (place_name, ps_name, zone, division)
    finally:
        with _in_flight_lock:
            _in_flight_buckets.discard(bucket_key)


def bulk_get_cached_locations(coords: List[Tuple[float, float]]) -> Dict[Tuple[Decimal, Decimal], Tuple[str, str, str, str]]:
    """
    Sub-millisecond batch retrieval of cached place names and jurisdictions for a list of coordinates.
    Guarantees ZERO external HTTP calls.
    Returns mapping: (lat_bucket, lon_bucket) -> (place_name, police_station, zone, division).
    """
    buckets = {get_bucket(lat, lon) for lat, lon in coords if lat is not None and lon is not None}
    if not buckets:
        return {}

    from django.db.models import Q
    # Query using batched Q filters for exact bucket pairs
    q_filter = Q()
    for lat_b, lon_b in buckets:
        q_filter |= Q(lat_bucket=lat_b, lon_bucket=lon_b)

    entries = GeocodingCache.objects.filter(q_filter)
    result = {}
    for e in entries:
        ps_name = e.police_station
        zone = e.zone
        division = e.division
        # Self-healing: if cached before boundaries were loaded, re-resolve via local PostGIS PIP
        if ps_name == 'Jurisdiction unavailable':
            res_ps, res_zone, res_div = resolve_ps_jurisdiction(float(e.lat_bucket), float(e.lon_bucket))
            if res_ps != 'Jurisdiction unavailable':
                ps_name, zone, division = res_ps, res_zone, res_div
        result[(e.lat_bucket, e.lon_bucket)] = (e.place_name, ps_name, zone, division)

    # For any bucket missing from cache, evaluate local PostGIS without network
    missing_buckets = buckets - set(result.keys())
    for lat_b, lon_b in missing_buckets:
        ps_name, zone, division = resolve_ps_jurisdiction(float(lat_b), float(lon_b))
        result[(lat_b, lon_b)] = ('Location unavailable', ps_name, zone, division)

    return result


def enrich_tracking_session_locations(session_id: int) -> int:
    """
    Background worker function that enriches all timeline-relevant coordinates for a tracking session.
    Enriches:
    - First point (Start location)
    - Sampled breadcrumbs
    - Last point (Latest / Final location)
    - Associated IdolEvents
    Adheres strictly to rate limits and persistent caching.
    """
    from apps.tracking.models import TrackingSession, LocationPoint, IdolEvent

    try:
        session = TrackingSession.objects.filter(id=session_id).select_related('assignment__idol').first()
        if not session:
            return 0

        coords_to_enrich = []

        # 1. Location points (first, last, and ~12 min sampled breadcrumbs)
        pts = list(LocationPoint.objects.filter(session=session).order_by('recorded_at'))
        if pts:
            coords_to_enrich.append((pts[0].latitude, pts[0].longitude))
            if len(pts) > 2:
                last_time = pts[0].recorded_at
                for pt in pts[1:-1]:
                    if (pt.recorded_at - last_time).total_seconds() >= 720.0:  # 12 minutes
                        coords_to_enrich.append((pt.latitude, pt.longitude))
                        last_time = pt.recorded_at
            if len(pts) > 1:
                coords_to_enrich.append((pts[-1].latitude, pts[-1].longitude))

        # 2. Operational IdolEvents
        idol = session.assignment.idol if session.assignment else None
        events = IdolEvent.objects.filter(
            models.Q(tracking_session=session) | models.Q(idol=idol, tracking_session__isnull=True)
        )
        for ev in events:
            if ev.latitude and ev.longitude:
                coords_to_enrich.append((ev.latitude, ev.longitude))

        # 3. Deduplicate by bucket
        unique_buckets = {}
        for lat, lon in coords_to_enrich:
            b = get_bucket(lat, lon)
            if b not in unique_buckets:
                unique_buckets[b] = (lat, lon)

        enriched_count = 0
        for (lat_b, lon_b), (lat, lon) in unique_buckets.items():
            if not GeocodingCache.objects.filter(lat_bucket=lat_b, lon_bucket=lon_b).exists():
                get_or_create_location_enrichment(lat, lon, allow_network=True)
                enriched_count += 1

        logger.info(f"Session {session_id} enriched {enriched_count} new location buckets.")
        return enriched_count
    except Exception as e:
        logger.warning(f"Error enriching session {session_id} locations: {e}")
        return 0


def trigger_async_session_enrichment(session_id: int):
    """
    Spawns a daemon thread to asynchronously enrich session locations without blocking HTTP request.
    """
    import sys
    if not session_id or 'test' in sys.argv:
        return
    t = threading.Thread(
        target=enrich_tracking_session_locations,
        args=(session_id,),
        name=f"EnrichSession-{session_id}",
        daemon=True
    )
    t.start()
