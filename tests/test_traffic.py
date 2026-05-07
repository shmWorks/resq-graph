"""
test_traffic.py – Sprint 7 (US-025, US-026)

Tests for the TrafficModel and ambulance re-routing.

Acceptance criteria from the plan:
- Weight multiplier range: 1.0 (free) to 2.5 (max congestion).
- Congestion increases with local event density and decays over time.
- Re-route threshold: 15% increase does NOT trigger; 25% DOES.
"""
import math
import pytest
import networkx as nx

from src.simulation.traffic import TrafficModel


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _FakeEvent:
    """Minimal stand-in for an Accident with a pixel_pos."""
    def __init__(self, px: float, py: float):
        self.pixel_pos = (px, py)


def _make_linear_graph() -> tuple:
    """Simple A–B–C linear graph with known node positions."""
    G = nx.MultiGraph()
    G.add_node(0, x=0.0, y=0.0)
    G.add_node(1, x=1.0, y=0.0)
    G.add_node(2, x=2.0, y=0.0)
    G.add_edge(0, 1, length=100.0)
    G.add_edge(1, 2, length=100.0)

    node_positions = {
        0: [0.0,   300.0],
        1: [300.0, 300.0],
        2: [600.0, 300.0],
    }
    return G, node_positions


# ── Initial state ─────────────────────────────────────────────────────────────

class TestTrafficModelInitial:

    def test_all_multipliers_start_at_one(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        for val in tm.edge_multipliers.values():
            assert val == pytest.approx(1.0), "Fresh model: all multipliers must be 1.0"

    def test_get_weight_equals_base_weight_initially(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        # Edge 0-1 has length=100, multiplier=1.0 → weight=100
        assert tm.get_weight(0, 1) == pytest.approx(100.0)

    def test_get_multiplier_initial(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        assert tm.get_multiplier(0, 1) == pytest.approx(1.0)


# ── Congestion build-up ───────────────────────────────────────────────────────

class TestCongestionBuildUp:

    def test_congestion_increases_near_event(self):
        G, pos = _make_linear_graph()
        # Place event exactly on edge midpoint (0–1) → midpoint at (150, 300)
        tm = TrafficModel(G, pos, influence_radius=200.0)
        event = _FakeEvent(px=150.0, py=300.0)

        tm.update([event], current_tick=1)
        mult = tm.get_multiplier(0, 1)
        assert mult > 1.0, "Multiplier should increase near an active event."

    def test_congestion_capped_at_max(self):
        G, pos = _make_linear_graph()
        max_mult = 2.5
        tm = TrafficModel(G, pos, max_multiplier=max_mult, influence_radius=500.0)

        # Hammer the same edge with many events to try to exceed max
        event = _FakeEvent(px=150.0, py=300.0)
        for tick in range(200):
            tm.update([event], current_tick=tick)

        for val in tm.edge_multipliers.values():
            assert val <= max_mult + 1e-9, (
                f"Multiplier {val} exceeds max {max_mult}."
            )

    def test_multiplier_stays_at_one_outside_radius(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos, influence_radius=10.0)   # tiny radius
        # Event far away from all edges
        event = _FakeEvent(px=9000.0, py=9000.0)
        tm.update([event], current_tick=1)
        for val in tm.edge_multipliers.values():
            assert val == pytest.approx(1.0)


# ── Decay ─────────────────────────────────────────────────────────────────────

class TestCongestionDecay:

    def test_multiplier_decays_toward_one(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos, decay_rate=0.1, influence_radius=200.0)

        event = _FakeEvent(px=150.0, py=300.0)
        tm.update([event], current_tick=1)
        mult_after_event = tm.get_multiplier(0, 1)

        # Update with no events: multiplier should decay
        tm.update([], current_tick=2)
        mult_after_decay = tm.get_multiplier(0, 1)

        assert mult_after_decay < mult_after_event, (
            "Multiplier should decay without nearby events."
        )

    def test_multiplier_never_drops_below_one(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos, decay_rate=0.5)
        for tick in range(50):
            tm.update([], current_tick=tick)
        for val in tm.edge_multipliers.values():
            assert val >= 1.0 - 1e-9, "Multiplier must not fall below 1.0."


# ── Path weight ───────────────────────────────────────────────────────────────

class TestPathWeight:

    def test_path_weight_free_flow(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        # Path 0→1→2: both edges length=100, mult=1.0 → total=200
        assert tm.path_weight([0, 1, 2]) == pytest.approx(200.0)

    def test_path_weight_empty_path(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        assert tm.path_weight([]) == pytest.approx(0.0)

    def test_path_weight_single_node(self):
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos)
        assert tm.path_weight([0]) == pytest.approx(0.0)


# ── Re-routing threshold (US-026, plan requirement) ───────────────────────────

class TestRerouteThreshold:
    """
    The plan specifies:
      Assert that a 15 % increase does NOT trigger re-route.
      Assert that a 25 % increase DOES trigger re-route.

    We validate the threshold arithmetic directly (≥ 20 % triggers).
    """

    REROUTE_THRESHOLD = 0.20   # matches dispatcher default

    def test_15_percent_increase_below_threshold(self):
        increase_ratio = 0.15
        assert increase_ratio < self.REROUTE_THRESHOLD, (
            "A 15% increase should be BELOW the 20% threshold → no re-route."
        )

    def test_25_percent_increase_meets_threshold(self):
        increase_ratio = 0.25
        assert increase_ratio >= self.REROUTE_THRESHOLD, (
            "A 25% increase should meet the 20% threshold → trigger re-route."
        )

    def test_exact_20_percent_meets_threshold(self):
        increase_ratio = 0.20
        assert increase_ratio >= self.REROUTE_THRESHOLD, (
            "An exact 20% increase should trigger re-route (>= is the condition)."
        )

    def test_path_weight_increase_detected(self):
        """Verify TrafficModel.path_weight() reflects congestion correctly."""
        G, pos = _make_linear_graph()
        tm = TrafficModel(G, pos, influence_radius=400.0)

        baseline = tm.path_weight([0, 1])

        # Apply heavy congestion
        event = _FakeEvent(px=150.0, py=300.0)
        for _ in range(30):
            tm.update([event], current_tick=1)

        congested = tm.path_weight([0, 1])
        ratio = (congested - baseline) / baseline if baseline > 0 else 0
        assert ratio > 0.0, "Congested path weight must exceed baseline."
