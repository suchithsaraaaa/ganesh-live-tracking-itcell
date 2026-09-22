"""
Common utilities for GPID validation, whitespace normalization, and geospatial helpers.
"""
import re

# GPID Anatomy: HYD - CMRZ - CMNR - 0234
GPID_REGEX = re.compile(r'^[A-Z0-9]{3,4}[A-Z0-9]{3,5}[A-Z0-9]{3,5}[0-9]{3,5}$')


def normalize_string(val):
    """Trim surrounding whitespace and collapse internal excessive whitespace."""
    if val is None:
        return ''
    s = str(val).strip()
    if s.lower() in ('nan', 'none', 'null'):
        return ''
    return s


def is_valid_gpid_format(gpid):
    """Check if string conforms to standard GPID format."""
    if not gpid:
        return False
    normalized = normalize_string(gpid)
    return bool(GPID_REGEX.match(normalized))
