"""
map_config.py – Sprint 1: Screen dimensions & coordinate conversion.

Defines the Pygame window size and provides the central
`latlon_to_pixel(lat, lon, bbox)` utility used by every rendering module.
"""

# ── Screen dimensions ──────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1200
SCREEN_HEIGHT = 900

# ── Padding (pixels kept clear around the map edges) ─────────────────────────
PADDING = 40


def latlon_to_pixel(lat: float, lon: float, bbox: tuple) -> tuple[int, int]:
    """Convert geographic coordinates to pixel coordinates.

    The bounding box is (min_lon, min_lat, max_lon, max_lat), matching the
    format used in map_loader.py.

    Parameters
    ----------
    lat : float
        Latitude of the point.
    lon : float
        Longitude of the point.
    bbox : tuple
        (min_lon, min_lat, max_lon, max_lat)

    Returns
    -------
    (px, py) : tuple[int, int]
        Pixel coordinates guaranteed to lie inside the drawable area
        [PADDING, SCREEN_WIDTH - PADDING] × [PADDING, SCREEN_HEIGHT - PADDING].
    """
    min_lon, min_lat, max_lon, max_lat = bbox

    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat

    if lon_range == 0 or lat_range == 0:
        raise ValueError("bbox has zero extent in at least one dimension.")

    drawable_w = SCREEN_WIDTH  - 2 * PADDING
    drawable_h = SCREEN_HEIGHT - 2 * PADDING

    # Longitude → x  (left = min_lon, right = max_lon)
    px = int(PADDING + (lon - min_lon) / lon_range * drawable_w)

    # Latitude → y   (top = max_lat, bottom = min_lat — y axis is flipped)
    py = int(PADDING + (max_lat - lat) / lat_range * drawable_h)

    # Clamp to drawable area (handles floating-point edge cases)
    px = max(PADDING, min(SCREEN_WIDTH  - PADDING, px))
    py = max(PADDING, min(SCREEN_HEIGHT - PADDING, py))

    return px, py
