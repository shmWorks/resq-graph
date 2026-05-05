"""
tests/test_map_config.py – Sprint 1 verification tests.

Covers:
    • latlon_to_pixel stays within SCREEN bounds (incl. padding).
    • node_positions.json covers all nodes in model_town.graphml.
"""

import os
import sys
import json
import pytest

# Make src/ importable when running pytest from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from map_config import latlon_to_pixel, SCREEN_WIDTH, SCREEN_HEIGHT, PADDING

# ── Bounding box used by map_loader ──────────────────────────────────────────
BBOX = (74.347, 31.505, 74.370, 31.535)   # (min_lon, min_lat, max_lon, max_lat)


# ─────────────────────────────────────────────────────────────────────────────
# latlon_to_pixel tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLatLonToPixel:
    """Unit tests for the coordinate conversion utility."""

    # Parametrised sample points inside the bbox
    _SAMPLES = [
        # (lat,    lon,    description)
        (31.505, 74.347, "bottom-left corner"),
        (31.535, 74.370, "top-right corner"),
        (31.520, 74.358, "centre"),
        (31.510, 74.350, "near bottom-left"),
        (31.530, 74.365, "near top-right"),
    ]

    @pytest.mark.parametrize("lat,lon,desc", _SAMPLES)
    def test_pixel_within_screen_width(self, lat, lon, desc):
        px, _ = latlon_to_pixel(lat, lon, BBOX)
        assert 0 <= px < SCREEN_WIDTH, (
            f"{desc}: px={px} outside [0, {SCREEN_WIDTH})"
        )

    @pytest.mark.parametrize("lat,lon,desc", _SAMPLES)
    def test_pixel_within_screen_height(self, lat, lon, desc):
        _, py = latlon_to_pixel(lat, lon, BBOX)
        assert 0 <= py < SCREEN_HEIGHT, (
            f"{desc}: py={py} outside [0, {SCREEN_HEIGHT})"
        )

    @pytest.mark.parametrize("lat,lon,desc", _SAMPLES)
    def test_pixel_respects_padding(self, lat, lon, desc):
        px, py = latlon_to_pixel(lat, lon, BBOX)
        assert PADDING <= px <= SCREEN_WIDTH  - PADDING, (
            f"{desc}: px={px} violates padding [{PADDING}, {SCREEN_WIDTH - PADDING}]"
        )
        assert PADDING <= py <= SCREEN_HEIGHT - PADDING, (
            f"{desc}: py={py} violates padding [{PADDING}, {SCREEN_HEIGHT - PADDING}]"
        )

    def test_x_increases_with_longitude(self):
        """Larger longitude → larger pixel x."""
        px1, _ = latlon_to_pixel(31.520, 74.350, BBOX)
        px2, _ = latlon_to_pixel(31.520, 74.365, BBOX)
        assert px2 > px1, "Pixel x should increase with longitude."

    def test_y_decreases_with_latitude(self):
        """Larger latitude → smaller pixel y (y-axis is flipped)."""
        _, py1 = latlon_to_pixel(31.510, 74.358, BBOX)
        _, py2 = latlon_to_pixel(31.530, 74.358, BBOX)
        assert py2 < py1, "Pixel y should decrease with latitude (y-flip)."

    def test_invalid_bbox_raises(self):
        with pytest.raises(ValueError):
            latlon_to_pixel(31.520, 74.358, (74.358, 31.520, 74.358, 31.520))


# ─────────────────────────────────────────────────────────────────────────────
# node_positions.json coverage test
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR       = os.path.join(os.path.dirname(__file__), "..", "data")
NODE_POS_PATH  = os.path.join(DATA_DIR, "node_positions.json")
GRAPH_PATH     = os.path.join(DATA_DIR, "model_town.graphml")


@pytest.mark.skipif(
    not os.path.exists(NODE_POS_PATH) or not os.path.exists(GRAPH_PATH),
    reason="data artefacts not present – run bake_map.py first",
)
class TestNodePositionsJson:
    """Verify node_positions.json matches the GraphML node set."""

    def test_all_nodes_present(self):
        import networkx as nx

        G = nx.read_graphml(GRAPH_PATH)
        graph_nodes = {str(n) for n in G.nodes()}

        with open(NODE_POS_PATH) as f:
            positions = json.load(f)
        json_nodes = set(positions.keys())

        missing = graph_nodes - json_nodes
        assert not missing, (
            f"{len(missing)} graph nodes are missing from node_positions.json:\n"
            f"  {list(missing)[:10]}…"
        )

    def test_positions_within_screen(self):
        with open(NODE_POS_PATH) as f:
            positions = json.load(f)

        for node_id, (px, py) in positions.items():
            assert 0 <= px < SCREEN_WIDTH,  f"Node {node_id}: px={px} out of bounds"
            assert 0 <= py < SCREEN_HEIGHT, f"Node {node_id}: py={py} out of bounds"
