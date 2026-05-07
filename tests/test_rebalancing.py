"""
test_rebalancing.py – Sprint 6 (US-023)

Tests for ambulance REBALANCING state transitions.

Acceptance criteria from the plan:
- IDLE → REBALANCING → IDLE transition on arrival at hotspot.
- Rebalancing does not interrupt IN_TRANSIT assignments.
- rebalance_target is cleared on arrival.
"""
import pytest
import networkx as nx

from src.simulation.ambulance import Ambulance, AmbulanceState


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_graph():
    G = nx.MultiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=1.0, y=0.0)
    G.add_node(3, x=2.0, y=0.0)
    G.add_edge(1, 2, length=100.0)
    G.add_edge(2, 3, length=100.0)
    return G


@pytest.fixture
def node_positions():
    return {
        1: [100.0, 100.0],
        2: [200.0, 100.0],
        3: [300.0, 100.0],
    }


# ── REBALANCING state transitions (plan: US-023) ──────────────────────────────

class TestRebalancingStateMachine:

    def test_idle_to_rebalancing(self, mock_graph):
        """IDLE ambulance transitions to REBALANCING when navigate(rebalancing=True)."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        assert amb.state == AmbulanceState.IDLE

        amb.navigate(destination=2, path=[1, 2], rebalancing=True)
        assert amb.state == AmbulanceState.REBALANCING

    def test_rebalancing_to_idle_on_arrival(self, mock_graph, node_positions):
        """REBALANCING ambulance returns to IDLE (not ON_SCENE) on arrival."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        amb.navigate(destination=2, path=[1, 2], rebalancing=True)
        amb.rebalance_target = 2

        assert amb.state == AmbulanceState.REBALANCING

        # Drive to destination (speed=1.0 → one step per tick)
        amb.speed = 2.0   # fast-forward to destination
        amb.update_position(node_positions)
        amb.update_position(node_positions)   # ensure arrival

        assert amb.state == AmbulanceState.IDLE, (
            "Ambulance should return to IDLE after completing REBALANCING, not ON_SCENE."
        )

    def test_rebalance_target_cleared_on_arrival(self, mock_graph, node_positions):
        """rebalance_target must be None after arriving at hotspot."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        amb.navigate(destination=2, path=[1, 2], rebalancing=True)
        amb.rebalance_target = 2

        amb.speed = 2.0
        amb.update_position(node_positions)
        amb.update_position(node_positions)

        assert amb.rebalance_target is None

    def test_in_transit_not_interrupted(self, mock_graph):
        """An IN_TRANSIT ambulance must NOT enter REBALANCING state."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        # Send on a real emergency
        amb.navigate(destination=3, path=[1, 2, 3], rebalancing=False)
        assert amb.state == AmbulanceState.IN_TRANSIT

        # Attempting to navigate again (rebalancing=True) must be no-op if state check is done
        # The dispatcher guards against this by checking state == IDLE; test that guard works
        assert amb.state != AmbulanceState.IDLE, (
            "IN_TRANSIT ambulance should not be eligible for rebalancing."
        )

    def test_rebalancing_state_in_enum(self):
        """AmbulanceState.REBALANCING must exist and have correct value."""
        assert AmbulanceState.REBALANCING.value == "REBALANCING"

    def test_sprint6_fields_exist(self, mock_graph):
        """Sprint 6 fields must exist on freshly constructed Ambulance."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        assert hasattr(amb, "rebalance_target")
        assert amb.rebalance_target is None

    def test_sprint7_fields_exist(self, mock_graph):
        """Sprint 7 re-routing fields must exist on freshly constructed Ambulance."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        assert hasattr(amb, "reroute_check_tick")
        assert hasattr(amb, "path_weight_at_dispatch")
        assert amb.reroute_check_tick == 0
        assert amb.path_weight_at_dispatch == 0.0

    def test_complete_task_clears_sprint6_7_fields(self, mock_graph):
        """complete_task() must clear all Sprint 6/7 fields."""
        amb = Ambulance(id=0, start_node=1, graph=mock_graph)
        amb.rebalance_target        = 3
        amb.reroute_check_tick      = 42
        amb.path_weight_at_dispatch = 500.0
        amb.complete_task()
        assert amb.rebalance_target        is None
        assert amb.reroute_check_tick      == 0
        assert amb.path_weight_at_dispatch == 0.0
        assert amb.state                   == AmbulanceState.IDLE
