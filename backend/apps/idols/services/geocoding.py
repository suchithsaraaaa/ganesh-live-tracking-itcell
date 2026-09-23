import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple, List
from django.conf import settings
from apps.idols.models import Idol, GeocodingStatus, GeocodingConfidence

logger = logging.getLogger(__name__)

# Hyderabad Metropolitan Operational Bounding Box (generous to include outer mandals)
HYDERABAD_LAT_MIN = 17.15
HYDERABAD_LAT_MAX = 17.70
HYDERABAD_LON_MIN = 78.15
HYDERABAD_LON_MAX = 78.75

# Nominatim Generic City Centroid (Mecca Masjid / Charminar)
CITY_CENTROID_LAT = 17.3605890
CITY_CENTROID_LON = 78.4740613


def is_within_hyderabad_bounds(lat: float, lon: float) -> bool:
    return (
        HYDERABAD_LAT_MIN <= lat <= HYDERABAD_LAT_MAX and
        HYDERABAD_LON_MIN <= lon <= HYDERABAD_LON_MAX
    )


def is_generic_city_centroid(lat: float, lon: float) -> bool:
    """Returns True if the coordinates are the generic Mecca Masjid / Hyderabad centroid."""
    return (abs(lat - CITY_CENTROID_LAT) < 0.001 and abs(lon - CITY_CENTROID_LON) < 0.001)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


PS_NAME_NORMALIZATION: Dict[str, str] = {
    'hussainialam': 'Hussaini Alam',
    'sanathnagar': 'Sanath Nagar',
    'begumbazar': 'Begum Bazar',
    'sultanbazar': 'Sultan Bazar',
    'habeebnagar': 'Habib Nagar',
    'mirchowk': 'Mir Chowk',
    'tappachabutra': 'Tappa Chabutra',
    'gandhinagar': 'Gandhi Nagar',
    'asifnagar': 'Asif Nagar',
    'santoshnagar': 'Santosh Nagar',
    'shahalibanda': 'Shah Ali Banda',
    'ou sity': 'Osmania University',
    'medipatnam': 'Mehdipatnam',
    'rein bazar': 'Rain Bazar',
    'lake': 'Hussain Sagar',
    'sr nagar': 'Sanjeeva Reddy Nagar',
    'is sadan': 'IS Sadan',
    'chatrinaka': 'Chatrinaka',
    'chilkalguda': 'Chilkalguda',
    'kulsumpura': 'Kulsumpura',
    'goshamahal': 'Goshamahal',
    'afzalgunj': 'Afzal Gunj',
    'amberpet': 'Amberpet',
    'moghalpura': 'Moghalpura',
    'chikkadpally': 'Chikkadpally',
    'kachiguda': 'Kacheguda',
    'musheerabad': 'Musheerabad',
    'saidabad': 'Saidabad',
    'langer house': 'Langer Houz',
    'kamatipura': 'Kamatipura',
    'warasiguda': 'Warasiguda',
    'malakpet': 'Malakpet',
    'narayanaguda': 'Narayanaguda',
    'domalguda': 'Domalguda',
    'rajendranagar': 'Rajendranagar',
    'attapur': 'Attapur',
    'borabanda': 'Borabanda',
    'film nagar': 'Film Nagar',
    'panjagutta': 'Panjagutta',
    'meerpet': 'Meerpet',
    'lalaguda': 'Lalaguda',
    'mailardevpally': 'Mailardevpally',
    'pahadishareef': 'Pahadi Shareef',
    'nallakunta': 'Nallakunta',
    'golconda': 'Golconda',
    'abids': 'Abids',
    'saifabad': 'Saifabad',
    'chaderghat': 'Chaderghat',
    'mangalhat': 'Mangalhat',
    'chandrayangutta': 'Chandrayangutta',
    'falaknuma': 'Falaknuma',
    'adibatla': 'Adibatla',
    'gudimalkapur': 'Gudimalkapur',
    'banjara hills': 'Banjara Hills',
    'masab tank': 'Masab Tank',
    'madhura nagar': 'Madhura Nagar',
    'khairatabad': 'Khairatabad',
    'nampally': 'Nampally',
    'mahankali': 'Mahankali Secunderabad',
    'ramgopalpet': 'Ramgopalpet',
    'charminar': 'Charminar',
    'madannapet': 'Madannapet',
    'bandlaguda': 'Bandlaguda',
    'balapur': 'Balapur',
    'bhavani nagar': 'Bhavani Nagar',
    'tolichowki': 'Tolichowki',
}


def normalize_police_station(ps: str) -> str:
    if not ps:
        return ""
    clean = ps.strip().lower()
    return PS_NAME_NORMALIZATION.get(clean, ps.strip())


def sanitize_address_for_geocoding(text: str) -> str:
    """
    Cleans excessive punctuation, whitespace, and house-number noise while
    PRESERVING:
    - 6-digit postal codes
    - Real street and colony names
    - Key geographic landmarks (temple, school, community hall, water tank)
    """
    if not text:
        return ""
    # Normalize newlines and carriage returns
    cleaned = text.replace('\r', ' ').replace('\n', ' ')

    # Remove house number prefixes like '21-4-330/1', 'H.No 12/B', 'Plot No 45'
    cleaned = re.sub(r'\b(h\.?no|house\s*no|plot\s*no|door\s*no|flat\s*no|d\.?no)\b[:\s\d/-]*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{1,4}[-/]\d{1,4}[-/]?\d{0,4}[A-Za-z0-9/]*\b', '', cleaned)

    # Remove generic administrative filler phrases (country, state, dist)
    cleaned = re.sub(r'\b(r\.?r\.?\s*dist(rict)?|hyderabad\s*dist(rict)?|telangana|india)\b', '', cleaned, flags=re.IGNORECASE)

    # Normalize punctuation and extra whitespace
    cleaned = re.sub(r'[,/\\;-]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class BaseGeocoder:
    def geocode_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def geocode_query(self, query: str) -> Optional[Tuple[float, float, str, str]]:
        cands = self.geocode_candidates(query, limit=1)
        if cands:
            c = cands[0]
            return float(c['lat']), float(c['lon']), c.get('display_name', ''), c.get('type', '')
        return None


class NominatimGeocoder(BaseGeocoder):
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "HyderabadPoliceGaneshTracking/1.0 (itcell@tspolice.gov.in)"

    def __init__(self, delay_sec: float = 1.1):
        self.delay_sec = delay_sec
        self.last_call_time = 0.0

    def geocode_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        elapsed = time.time() - self.last_call_time
        if elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)

        params = urllib.parse.urlencode({
            'q': query,
            'format': 'json',
            'limit': limit,
            'countrycodes': 'in',
            'addressdetails': 1
        })
        url = f"{self.BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': self.USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.last_call_time = time.time()
                data = json.loads(resp.read().decode('utf-8'))
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Nominatim error for query '{query}': {e}")
            self.last_call_time = time.time()
            return []


class MockGeocoder(BaseGeocoder):
    """
    Deterministic mock geocoder for tests and dry runs without external network calls.
    Returns valid candidates inside Hyderabad.
    """
    def geocode_candidates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        q_hash = abs(hash(query))
        lat = 17.3600 + (q_hash % 1000) * 0.0001
        lon = 78.4700 + ((q_hash // 1000) % 1000) * 0.0001
        return [{
            'lat': str(lat),
            'lon': str(lon),
            'display_name': f"Mock Location for {query}",
            'type': 'residential' if 'nagar' in query.lower() or 'street' in query.lower() else 'suburb',
            'address': {
                'state': 'Telangana',
                'postcode': '500053' if '500053' in query else '500001',
                'suburb': 'Mock Suburb',
                'city': 'Hyderabad'
            }
        }]


def get_geocoder(provider: Optional[str] = None) -> BaseGeocoder:
    selected = provider or getattr(settings, 'GEOCODING_PROVIDER', 'nominatim')
    if str(selected).lower() == 'mock':
        return MockGeocoder()
    return NominatimGeocoder()


def score_candidate(candidate: Dict[str, Any], idol: Idol, query_level: str) -> Optional[Tuple[float, float, str, str, str]]:
    """
    Scores and validates a geocoding candidate against the authoritative source data.
    Enforces strict invariants:
    1. Must lie inside Hyderabad bounds.
    2. Must be in Telangana.
    3. Must NOT be the generic city centroid (17.360589, 78.4740613).
    4. Postcode match gives highest confidence.
    5. Returns (lat, lon, display_name, result_type, confidence_level) or None if rejected.
    """
    try:
        lat = float(candidate['lat'])
        lon = float(candidate['lon'])
    except (KeyError, ValueError, TypeError):
        return None

    # 1. Bounding box check
    if not is_within_hyderabad_bounds(lat, lon):
        return None

    # 2. Reject generic city centroid
    if is_generic_city_centroid(lat, lon):
        return None

    addr = candidate.get('address', {})
    state = addr.get('state', '')
    if state and 'telangana' not in state.lower():
        return None

    cand_postcode = (addr.get('postcode', '') or '').strip()
    idol_pin = (idol.instal_pin or '').strip()
    display_name = candidate.get('display_name', '')
    village_lower = (idol.instal_village or '').strip().lower()
    ps_lower = (idol.police_station or '').strip().lower()

    # Reject homonym localities in distant postal zones
    locality_matches = bool((village_lower and village_lower in display_name.lower()) or (ps_lower and ps_lower in display_name.lower()))
    if cand_postcode and idol_pin and cand_postcode != idol_pin and not locality_matches:
        # Candidate is in a different postal zone and does not match idol village or police station
        return None

    res_type = candidate.get('type', '')

    # Determine confidence level
    # EXACT: Building, premise, place of worship, clinic, school
    if res_type in ('building', 'house', 'place_of_worship', 'amenity', 'temple', 'clinic', 'school', 'hospital', 'community_centre', 'apartments'):
        if cand_postcode and idol_pin and cand_postcode != idol_pin:
            conf = GeocodingConfidence.MEDIUM
        else:
            conf = GeocodingConfidence.EXACT
    # HIGH: Road, residential street, lane with matching PIN/locality
    elif res_type in ('road', 'residential', 'living_street', 'neighbourhood', 'pedestrian', 'tertiary', 'secondary', 'primary') and query_level == 'street':
        if cand_postcode and idol_pin and cand_postcode != idol_pin:
            conf = GeocodingConfidence.MEDIUM
        else:
            conf = GeocodingConfidence.HIGH
    # MEDIUM: Suburb, village, quarter, locality
    elif res_type in ('suburb', 'village', 'quarter', 'locality', 'hamlet') or query_level in ('village', 'locality'):
        conf = GeocodingConfidence.MEDIUM
    else:
        # Generic city/administrative boundaries without street or suburb
        if res_type in ('city', 'administrative', 'state'):
            return None
        conf = GeocodingConfidence.MEDIUM

    return lat, lon, display_name, res_type, conf


def geocode_idol(idol: Idol, geocoder: Optional[BaseGeocoder] = None) -> Dict[str, Any]:
    """
    Safely resolves geographic coordinates for an Idol without transmitting sensitive personal data.
    Constructs structured queries prioritizing PIN code and specific street/locality.
    Strictly prohibits:
    - Police Station centroid queries
    - Generic City Centroid queries
    - Arbitrary coordinate offsets
    """
    if geocoder is None:
        geocoder = get_geocoder()

    street_clean = sanitize_address_for_geocoding(idol.instal_street)
    village_clean = sanitize_address_for_geocoding(idol.instal_village)
    addr_clean = sanitize_address_for_geocoding(idol.address)
    pin = (idol.instal_pin or '').strip()

    # Build prioritized candidate queries
    # Format: (query_string, query_level)
    queries: List[Tuple[str, str]] = []

    # Priority 1: Street + Locality/Village + PIN + Telangana, India
    if street_clean and village_clean and pin and len(street_clean) > 2 and street_clean.lower() != village_clean.lower():
        queries.append((f"{street_clean}, {village_clean}, {pin}, Telangana, India", "street"))

    # Priority 2: Street + PIN + Telangana, India
    if street_clean and pin and len(street_clean) > 2:
        queries.append((f"{street_clean}, {pin}, Telangana, India", "street"))

    # Priority 3: Full Address Line (if distinct from street) + PIN + Telangana, India
    if addr_clean and pin and len(addr_clean) > 3 and addr_clean != street_clean:
        queries.append((f"{addr_clean}, {pin}, Telangana, India", "street"))

    # Priority 4: Village / Sub-locality + PIN + Telangana, India
    if village_clean and pin and len(village_clean) > 2:
        queries.append((f"{village_clean}, {pin}, Telangana, India", "village"))

    # Priority 5: Street + Locality + Hyderabad, Telangana (if PIN query yielded no results)
    if street_clean and village_clean and len(street_clean) > 2 and street_clean.lower() != village_clean.lower():
        queries.append((f"{street_clean}, {village_clean}, Hyderabad, Telangana, India", "street"))

    # Priority 6: Village / Sub-locality + Hyderabad, Telangana (approximate locality level)
    if village_clean and len(village_clean) > 2 and village_clean.lower() != 'hyderabad':
        queries.append((f"{village_clean}, Hyderabad, Telangana, India", "locality"))

    seen_queries = set()
    best_candidate = None

    for query_str, query_level in queries:
        if query_str in seen_queries:
            continue
        seen_queries.add(query_str)

        candidates = geocoder.geocode_candidates(query_str, limit=5)
        for cand in candidates:
            scored = score_candidate(cand, idol, query_level)
            if scored:
                lat, lon, display_name, res_type, conf = scored
                # Prefer EXACT or HIGH over MEDIUM
                if conf in (GeocodingConfidence.EXACT, GeocodingConfidence.HIGH):
                    return {
                        'latitude': Decimal(str(round(lat, 7))),
                        'longitude': Decimal(str(round(lon, 7))),
                        'status': GeocodingStatus.GEOCODED,
                        'confidence': conf,
                        'resolved_address': display_name,
                        'result_type': res_type,
                        'query_used': query_str,
                        'provider': geocoder.__class__.__name__
                    }
                elif not best_candidate:
                    best_candidate = {
                        'latitude': Decimal(str(round(lat, 7))),
                        'longitude': Decimal(str(round(lon, 7))),
                        'status': GeocodingStatus.PARTIAL,
                        'confidence': conf,
                        'resolved_address': display_name,
                        'result_type': res_type,
                        'query_used': query_str,
                        'provider': geocoder.__class__.__name__
                    }

    if best_candidate:
        return best_candidate

    # Unresolved: No fake coordinates
    return {
        'latitude': None,
        'longitude': None,
        'status': GeocodingStatus.UNRESOLVED,
        'confidence': GeocodingConfidence.UNRESOLVED,
        'resolved_address': '',
        'result_type': '',
        'query_used': queries[0][0] if queries else '',
        'provider': geocoder.__class__.__name__
    }
