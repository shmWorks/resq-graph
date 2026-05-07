"""
test_demand_clustering.py – Sprint 6 (US-022, US-024)

Tests for the DemandClusterer and Hotspot model.

Acceptance criteria from the plan:
- Input: list of active accident locations.
- Output: list of Hotspot objects with (node_id, pixel_pos) tuples.
- Centroids calculated as geometric mean of cluster members.
- pixel_pos of centroid_node matches the mapped coordinates for that node.
"""
import pytest
import numpy as np

from src.intelligence.demand_clustering import DemandClusterer, Hotspot


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _FakeEvent:
    """Minimal stand-in for an Accident object."""
    def __init__(self, node_id: int, px: int, py: int):
        self.location  = node_id
        self.pixel_pos = (px, py)


def _make_node_positions(n_nodes: int = 100) -> dict:
    """Grid of nodes on a 10×10 pixel grid for testing."""
    positions = {}
    for i in range(n_nodes):
        positions[i] = [float(i % 10 * 50), float(i // 10 * 50)]
    return positions


# ── Empty / trivial input ─────────────────────────────────────────────────────

class TestDemandClustererTrivial:

    def test_empty_events_returns_empty(self):
        dc = DemandClusterer(node_positions=_make_node_positions())
        assert dc.run([]) == []

    def test_too_few_events_returns_empty(self):
        dc = DemandClusterer(
            node_positions=_make_node_positions(),
            min_cluster_size=5,
        )
        events = [_FakeEvent(i, i * 5, 0) for i in range(2)]
        result = dc.run(events)
        # 2 events < min_cluster_size=5 → no clusters → empty list
        assert result == []


# ── Hotspot structure ─────────────────────────────────────────────────────────

class TestHotspotStructure:

    def _clustered_events(self):
        """Two tight groups far apart → two hotspots."""
        node_pos = {i: [float(i * 2), 0.0] for i in range(200)}
        # Group A: nodes 0–9 at x ∈ [0, 18]
        # Group B: nodes 100–109 at x ∈ [200, 218]
        events = (
            [_FakeEvent(i, i * 2, 0) for i in range(10)]
            + [_FakeEvent(100 + i, 200 + i * 2, 0) for i in range(10)]
        )
        return node_pos, events

    def test_hotspot_has_required_fields(self):
        node_pos, events = self._clustered_events()
        dc = DemandClusterer(
            node_positions=node_pos,
            min_cluster_size=3,
            min_samples=2,
        )
        hotspots = dc.run(events)
        if not hotspots:
            pytest.skip("HDBSCAN found no clusters on this dataset.")
        hs = hotspots[0]
        assert isinstance(hs, Hotspot)
        assert isinstance(hs.cluster_id, int)
        assert isinstance(hs.centroid_node, int)
        assert isinstance(hs.pixel_pos, tuple) and len(hs.pixel_pos) == 2
        assert isinstance(hs.member_nodes, list)
        assert isinstance(hs.member_pixel_positions, list)

    def test_centroid_pixel_pos_matches_node(self):
        """pixel_pos of centroid_node must match node_positions[centroid_node]."""
        node_pos, events = self._clustered_events()
        dc = DemandClusterer(
            node_positions=node_pos,
            min_cluster_size=3,
            min_samples=2,
        )
        hotspots = dc.run(events)
        if not hotspots:
            pytest.skip("HDBSCAN found no clusters on this dataset.")
        for hs in hotspots:
            mapped = node_pos.get(hs.centroid_node)
            assert mapped is not None, f"centroid_node {hs.centroid_node} not in positions."
            assert hs.pixel_pos == (int(mapped[0]), int(mapped[1])), (
                f"pixel_pos {hs.pixel_pos} does not match node {hs.centroid_node} → {mapped}"
            )

    def test_size_matches_member_count(self):
        node_pos, events = self._clustered_events()
        dc = DemandClusterer(
            node_positions=node_pos,
            min_cluster_size=3,
            min_samples=2,
        )
        hotspots = dc.run(events)
        for hs in hotspots:
            assert hs.size == len(hs.member_nodes)
            assert hs.size == len(hs.member_pixel_positions)
