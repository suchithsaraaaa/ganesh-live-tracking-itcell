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


def get_zone_variants(val: str | None) -> list[str]:
    """
    Returns all common representations (with space, without space, canonical, raw)
    so queries match records across models regardless of legacy spacing in secondary tables.
    E.g. for 'Rajendra Nagar': ['Rajendra Nagar', 'Rajendranagar']
    """
    if not val:
        return []
    cleaned = str(val).strip()
    canonical = normalize_zone(cleaned)
    variants = {cleaned}
    if canonical:
        variants.add(canonical)
        variants.add(canonical.replace(' ', ''))
    return list(variants)


def zone_filter_q(field_name: str, val: str | None) -> Q:
    """
    Constructs a Django Q object matching any variant of the zone for the given field name.
    E.g. zone_filter_q('zone', 'Rajendra Nagar') matches zone__in=['Rajendra Nagar', 'Rajendranagar']
    """
    if not val or val.lower() in ('all', 'all zones', ''):
        return Q()
    variants = get_zone_variants(val)
    return Q(**{f"{field_name}__in": variants})
