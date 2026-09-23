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
    Strips noise, newlines, plot/house numbers like '21-4-330/1' or 'H.No: 12-3',
    leaving recognizable street and locality names for the geocoder.
    """
    if not text:
        return ""
    # Normalize newlines and carriage returns to spaces
    cleaned = text.replace('\r', ' ').replace('\n', ' ')
    # Strip landmark prepositions like 'opp to ...', 'opposite ...', 'near ...', 'beside ...'
    cleaned = re.sub(r'\b(opp(\.?|osite)|near|beside|behind|adj(\.?|acent))\s+(to\s+)?[^,]+', '', cleaned, flags=re.IGNORECASE)
    # Remove house number prefixes like '21-4-330/1', '12-3-45', 'H.No 12'
    cleaned = re.sub(r'\b\d{1,4}[-/]\d{1,4}[-/]?\d{0,4}[A-Za-z0-9/]*\b', '', cleaned)
    cleaned = re.sub(r'\b(h\.?no|house\s*no|plot\s*no|door\s*no)\b[:\s\d/-]*', '', cleaned, flags=re.IGNORECASE)
    # Remove common administrative suffix noise
    cleaned = re.sub(r'\b(r\.?r\.?\s*dist(rict)?|telangana|india|\d{6})\b', '', cleaned, flags=re.IGNORECASE)
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
    Only sends geographic components (street, village/locality, police station).
    Applies a structured multi-tier fallback pipeline.
    Zero fabricated coordinates: returns UNRESOLVED with None coordinates if unverified.
    """
    if geocoder is None:
        geocoder = get_geocoder()

    # Build sanitized geographic components (STRICTLY NO OWNER, NO MOBILE, NO CONSTABLE)
    street_clean = sanitize_address_for_geocoding(idol.instal_street)
    addr_clean = sanitize_address_for_geocoding(idol.address)
    ps_norm = normalize_police_station(idol.police_station)
    village_clean = sanitize_address_for_geocoding(idol.instal_village)

    queries: list[Tuple[str, str, str]] = []

    # Strategy 1: Street + Locality/PS + Hyderabad
    if street_clean and len(street_clean) > 3:
        if ps_norm and ps_norm.lower() not in street_clean.lower():
            queries.append((f"{street_clean}, {ps_norm}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "high"))
            queries.append((f"{street_clean}, {ps_norm}, Telangana, India", GeocodingStatus.GEOCODED, "high"))
        queries.append((f"{street_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "high"))
        queries.append((f"{street_clean}, Telangana, India", GeocodingStatus.GEOCODED, "high"))

    # Strategy 2: Clean Address Line + PS / Hyderabad / Telangana
    if addr_clean and addr_clean != street_clean and len(addr_clean) > 3:
        if ps_norm and ps_norm.lower() not in addr_clean.lower():
            queries.append((f"{addr_clean}, {ps_norm}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "medium"))
            queries.append((f"{addr_clean}, {ps_norm}, Telangana, India", GeocodingStatus.GEOCODED, "medium"))
        queries.append((f"{addr_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "medium"))
        queries.append((f"{addr_clean}, Telangana, India", GeocodingStatus.GEOCODED, "medium"))

        # Strategy 2B: Sub-token exploration if address contains commas/spaces (e.g. "Iqbal Gunj, Puranapul")
        parts = [p.strip() for p in re.split(r'[,]+', idol.address or '') if len(p.strip()) > 3]
        for part in parts:
            p_clean = sanitize_address_for_geocoding(part)
            if p_clean and len(p_clean) > 3 and p_clean != addr_clean:
                queries.append((f"{p_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "medium"))
                queries.append((f"{p_clean}, Telangana, India", GeocodingStatus.GEOCODED, "medium"))

    # Strategy 3: Village / Sub-locality if distinct
    if village_clean and village_clean not in [street_clean, addr_clean] and len(village_clean) > 3:
        queries.append((f"{village_clean}, Hyderabad, Telangana, India", GeocodingStatus.GEOCODED, "medium"))
        queries.append((f"{village_clean}, Telangana, India", GeocodingStatus.GEOCODED, "medium"))

    # Strategy 4: Police Station area jurisdiction (Partial / Locality level)
    if ps_norm:
        queries.append((f"{ps_norm}, Hyderabad, Telangana, India", GeocodingStatus.PARTIAL, "locality"))
        queries.append((f"{ps_norm}, Telangana, India", GeocodingStatus.PARTIAL, "locality"))

    seen_queries = set()
    for query_str, candidate_status, confidence_label in queries:
        if query_str in seen_queries:
            continue
        seen_queries.add(query_str)

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
