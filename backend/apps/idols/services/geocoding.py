import json
import logging
import re
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from apps.idols.models import Idol, GeocodingStatus

logger = logging.getLogger(__name__)

# Hyderabad Metropolitan Operational Bounding Box (generous to include outer mandals)
HYDERABAD_LAT_MIN = 17.15
HYDERABAD_LAT_MAX = 17.70
HYDERABAD_LON_MIN = 78.15
HYDERABAD_LON_MAX = 78.75


def is_within_hyderabad_bounds(lat: float, lon: float) -> bool:
    return (
        HYDERABAD_LAT_MIN <= lat <= HYDERABAD_LAT_MAX and
        HYDERABAD_LON_MIN <= lon <= HYDERABAD_LON_MAX
    )


def sanitize_address_for_geocoding(text: str) -> str:
    """
    Strips noise, plot/house numbers like '21-4-330/1' or 'H.No: 12-3',
    leaving recognizable street and locality names for the geocoder.
    """
    if not text:
        return ""
    # Remove house number prefixes like '21-4-330/1', '12-3-45', 'H.No 12'
    cleaned = re.sub(r'\b\d{1,4}[-/]\d{1,4}[-/]?\d{0,4}[A-Za-z0-9/]*\b', '', text)
    cleaned = re.sub(r'\b(h\.?no|house\s*no|plot\s*no|door\s*no)\b[:\s\d/-]*', '', cleaned, flags=re.IGNORECASE)
    # Remove stray punctuation and extra whitespace
    cleaned = re.sub(r'[,/\\;-]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class BaseGeocoder:
    def geocode_query(self, query: str) -> Optional[Tuple[float, float, str, str]]:
        raise NotImplementedError


class NominatimGeocoder(BaseGeocoder):
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "HyderabadPoliceGaneshTracking/1.0 (itcell@tspolice.gov.in)"

    def __init__(self, delay_sec: float = 1.1):
        self.delay_sec = delay_sec
        self.last_call_time = 0.0

    def geocode_query(self, query: str) -> Optional[Tuple[float, float, str, str]]:
        # Enforce polite rate limiting for OpenStreetMap Nominatim
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)

        params = urllib.parse.urlencode({
            'q': query,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'in',
        })
        url = f"{self.BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': self.USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.last_call_time = time.time()
                data = json.loads(resp.read().decode('utf-8'))
                if data and len(data) > 0:
                    top = data[0]
                    lat = float(top['lat'])
                    lon = float(top['lon'])
                    display_name = top.get('display_name', '')
                    result_type = top.get('type', 'locality')
                    return lat, lon, display_name, result_type
        except Exception as e:
            logger.warning(f"Nominatim error for query '{query}': {e}")
            self.last_call_time = time.time()
            return None

        return None


class MockGeocoder(BaseGeocoder):
    """
    Deterministic mock geocoder for tests and dry runs without external network calls.
    Returns valid coordinates within Hyderabad.
    """
    def geocode_query(self, query: str) -> Optional[Tuple[float, float, str, str]]:
        # Return deterministic coordinate based on query hash
        q_hash = abs(hash(query))
        lat = 17.3600 + (q_hash % 1000) * 0.0001
        lon = 78.4700 + ((q_hash // 1000) % 1000) * 0.0001
        return lat, lon, f"Mock Location for {query}", "mock"


def get_geocoder(provider: Optional[str] = None) -> BaseGeocoder:
    selected = provider or getattr(settings, 'GEOCODING_PROVIDER', 'nominatim')
    if str(selected).lower() == 'mock':
        return MockGeocoder()
    return NominatimGeocoder()


def geocode_idol(idol: Idol, geocoder: Optional[BaseGeocoder] = None) -> Dict[str, Any]:
    """
    Safely resolves geographic coordinates for an Idol without transmitting sensitive personal data.
    Only sends geographic components (street, village/locality, police station, Hyderabad).
    Applies a structured multi-tier fallback pipeline.
    """
    if geocoder is None:
        geocoder = get_geocoder()

    # Build sanitized geographic components (STRICTLY NO OWNER, NO MOBILE, NO CONSTABLE)
    street_clean = sanitize_address_for_geocoding(idol.instal_street or idol.address)
    ps_clean = idol.police_station.strip() if idol.police_station else ""
    pin_clean = idol.instal_pin.strip() if idol.instal_pin and len(idol.instal_pin.strip()) == 6 else ""

    # Strategy 1: Street + Locality + Hyderabad
    queries = []
    if street_clean and len(street_clean) > 3:
        if ps_clean and ps_clean.lower() not in street_clean.lower():
            queries.append((f"{street_clean}, {ps_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "high"))
        queries.append((f"{street_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "high"))

    # Strategy 2: Address line clean + Hyderabad
    addr_clean = sanitize_address_for_geocoding(idol.address)
    if addr_clean and addr_clean != street_clean and len(addr_clean) > 3:
        queries.append((f"{addr_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "medium"))

    # Strategy 3: Police Station area jurisdiction + Hyderabad (Low confidence / Area)
    if ps_clean:
        queries.append((f"{ps_clean}, Hyderabad, Telangana, India", GeocodingStatus.PARTIAL, "locality"))

    for query_str, candidate_status, confidence_label in queries:
        res = geocoder.geocode_query(query_str)
        if res:
            lat, lon, display_name, res_type = res
            if is_within_hyderabad_bounds(lat, lon):
                return {
                    'latitude': Decimal(str(round(lat, 7))),
                    'longitude': Decimal(str(round(lon, 7))),
                    'status': candidate_status,
                    'confidence': confidence_label,
                    'query_used': query_str,
                    'display_name': display_name,
                    'provider': geocoder.__class__.__name__
                }
            else:
                logger.warning(f"Geocoded coordinate ({lat}, {lon}) outside Hyderabad bounds for query: {query_str}")

    return {
        'latitude': None,
        'longitude': None,
        'status': GeocodingStatus.UNRESOLVED,
        'confidence': 'unresolved',
        'query_used': queries[0][0] if queries else '',
        'display_name': '',
        'provider': geocoder.__class__.__name__
    }
