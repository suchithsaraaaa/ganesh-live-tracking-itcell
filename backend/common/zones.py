"""
Authoritative Hyderabad Police Zone Definitions and Canonical Normalization.
Authoritative source: Hyderabad Police Master Dataset (14,930 / 15,414 GPIDs).
"""
from django.db.models import Q

AUTHORITATIVE_ZONES = [
    'Charminar',
    'Golconda',
    'Jubilee Hills',
    'Khairatabad',
    'Rajendra Nagar',
    'Secunderabad',
    'Shamshabad',
]

# Normalized key (stripped of whitespace, hyphens, lowercase) -> Canonical Name
_ZONE_CANONICAL_INDEX = {
    z.replace(' ', '').replace('-', '').replace('_', '').lower(): z
    for z in AUTHORITATIVE_ZONES
}

# Explicit aliases for common variations across legacy schemas/inputs
_ZONE_CANONICAL_INDEX.update({
    'rajendranagar': 'Rajendra Nagar',
    'rajendra nagar': 'Rajendra Nagar',
    'rajendranagarzone': 'Rajendra Nagar',
    'jubileehills': 'Jubilee Hills',
    'jubilee hills': 'Jubilee Hills',
    'jubileehillszone': 'Jubilee Hills',
    'secunderabad': 'Secunderabad',
    'secunderabadzone': 'Secunderabad',
    'charminar': 'Charminar',
    'charminarzone': 'Charminar',
    'golconda': 'Golconda',
    'golcondazone': 'Golconda',
    'khairatabad': 'Khairatabad',
    'khairatabadzone': 'Khairatabad',
    'shamshabad': 'Shamshabad',
    'shamshabadzone': 'Shamshabad',
})


def normalize_zone(val: str | None) -> str | None:
    """
    Normalizes any zone string representation to its authoritative canonical form.
    E.g. 'Rajendranagar' -> 'Rajendra Nagar', 'rajendra nagar' -> 'Rajendra Nagar'.
    If the value is empty or not in the index, returns the trimmed value.
    """
    if not val:
        return val
    cleaned = str(val).strip()
    key = cleaned.replace(' ', '').replace('-', '').replace('_', '').lower()
    return _ZONE_CANONICAL_INDEX.get(key, cleaned)


def are_same_zone(z1: str | None, z2: str | None) -> bool:
    """
    Compares two zone strings using canonical normalization.
    Returns True if both represent the same canonical zone (e.g. 'Rajendranagar' vs 'Rajendra Nagar').
    """
    if not z1 or not z2:
        return False
    cz1 = str(z1).strip().lower()
    cz2 = str(z2).strip().lower()
    if cz1 in ['all', 'all zones', 'city-wide', 'city wide', 'citywide'] or cz2 in ['all', 'all zones', 'city-wide', 'city wide', 'citywide']:
        return cz1 == cz2
    n1 = normalize_zone(z1) or z1
    n2 = normalize_zone(z2) or z2
    k1 = str(n1).replace(' ', '').replace('-', '').replace('_', '').lower()
    k2 = str(n2).replace(' ', '').replace('-', '').replace('_', '').lower()
    return k1 == k2


def get_zone_variants(val: str | None) -> list[str]:
    """
    Returns all common representations (with space, without space, canonical, raw,
    title case, capitalized, and lowercase) so queries match records across models
    regardless of legacy spacing or casing in secondary tables.
    E.g. for 'Rajendra Nagar': ['Rajendra Nagar', 'Rajendranagar', 'RajendraNagar', 'rajendranagar', 'rajendra nagar']
    """
    if not val:
        return []
    cleaned = str(val).strip()
    canonical = normalize_zone(cleaned) or cleaned
    nospace = canonical.replace(' ', '').replace('-', '').replace('_', '')

    variants = {
        cleaned,
        cleaned.lower(),
        canonical,
        canonical.lower(),
        canonical.upper(),
        nospace,
        nospace.capitalize(),
        nospace.lower(),
        nospace.upper(),
    }
    return sorted(list(variants))


def zone_filter_q(field_name: str, val: str | None) -> Q:
    """
    Constructs a Django Q object matching any variant of the zone for the given field name.
    E.g. zone_filter_q('zone', 'Rajendra Nagar') matches zone__in=['Rajendra Nagar', 'Rajendranagar']
    """
    if not val or val.lower() in ('all', 'all zones', ''):
        return Q()
    variants = get_zone_variants(val)
    return Q(**{f"{field_name}__in": variants})


import re

# Canonical police station alias mapping for known spelling / phonetic variants across tables
_PS_CANONICAL_INDEX = {
    'rajendranagar': 'Rajendranagar',
    'rajendranagarps': 'Rajendranagar',
    'rajendranagarpolicestation': 'Rajendranagar',
    'bhavaninagar': 'Bhavani Nagar',
    'reinbazar': 'Rein Bazar',
    'langerhouse': 'Langar House',
    'langarhouse': 'Langar House',
    'medipatnam': 'Mehdipatnam',
    'mehdipatnam': 'Mehdipatnam',
}


def _clean_ps_key(val: str | None) -> str:
    """
    Extracts a stripped, alphanumeric lowercase key for police station comparisons.
    Handles 'PS', 'Police Station', spaces, hyphens, and periods.
    """
    if not val:
        return ''
    cleaned = str(val).strip()
    base = re.sub(r'\b(police\s*station|ps)\b', '', cleaned, flags=re.IGNORECASE).strip()
    key = re.sub(r'[^a-zA-Z0-9]', '', base).lower()
    return _PS_CANONICAL_INDEX.get(key, key)


def normalize_ps_name(val: str | None) -> str | None:
    """
    Returns canonical display name of a police station if mapped, or trimmed original string.
    """
    if not val:
        return val
    cleaned = str(val).strip()
    key = _clean_ps_key(cleaned)
    return _PS_CANONICAL_INDEX.get(key, cleaned)


def are_same_ps(ps1: str | None, ps2: str | None) -> bool:
    """
    Compares two police station names handling harmless casing, spacing,
    punctuation differences, and canonical representations (e.g. 'Rajendra Nagar' vs 'Rajendranagar').
    """
    if not ps1 or not ps2:
        return False
    k1 = _clean_ps_key(ps1)
    k2 = _clean_ps_key(ps2)
    return bool(k1 and k2 and k1 == k2)


def get_ps_variants(val: str | None) -> list[str]:
    """
    Returns query variants for a police station so queries match across models
    regardless of spacing, casing, or legacy representation differences.
    """
    if not val:
        return []
    cleaned = str(val).strip()
    base = re.sub(r'\b(police\s*station|ps)\b', '', cleaned, flags=re.IGNORECASE).strip()
    nospace = re.sub(r'[^a-zA-Z0-9]', '', base)

    variants = {
        cleaned,
        cleaned.lower(),
        cleaned.upper(),
        base,
        base.lower(),
        base.upper(),
        nospace,
        nospace.lower(),
        nospace.upper(),
        nospace.capitalize(),
    }
    key = _clean_ps_key(val)
    if key in ('rajendranagar', 'rajendranagarps'):
        variants.update(['Rajendranagar', 'Rajendra Nagar', 'rajendranagar', 'rajendra nagar', 'RajendraNagar'])
    elif key == 'bhavaninagar':
        variants.update(['Bhavaninagar', 'Bhavani Nagar', 'bhavaninagar', 'bhavani nagar'])
    elif key == 'reinbazar':
        variants.update(['Reinbazar', 'Rein Bazar', 'reinbazar', 'rein bazar'])
    elif key == 'langarhouse':
        variants.update(['Langar House', 'Langer House', 'langarhouse', 'langerhouse', 'LangarHouse', 'LangerHouse'])
    elif key == 'mehdipatnam':
        variants.update(['Mehdipatnam', 'Medipatnam', 'mehdipatnam', 'medipatnam'])

    return sorted(list(variants))


def ps_filter_q(field_name: str, val: str | None) -> Q:
    """
    Constructs a Django Q object matching any variant of the police station for the given field name.
    E.g. ps_filter_q('police_station', 'Rajendra Nagar') matches police_station__in=['Rajendranagar', 'Rajendra Nagar']
    """
    if not val or val.lower() in ('all', 'all police stations', ''):
        return Q()
    variants = get_ps_variants(val)
    return Q(**{f"{field_name}__in": variants})
