"""
test_simulation_engine.py – Sprint 5 (US-020)

Integration tests for the full tick loop using DispatcherBrain.
"""
import pytest
import numpy as np
import networkx as nx

from src.simulation.simulation_engine import SimulationState, _tick
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import EventSpawner, Accident
from src.simulation.dispatcher import DispatcherBrain


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_graph():
    G = nx.MultiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=1.0, y=1.0)
    G.add_edge(1, 2, length=141.4)
    return G


@pytest.fixture
def node_positions():
    return {
        1: [100, 100],
        2: [200, 200],
    }


@pytest.fixture
def distance_matrix_and_index(mock_graph):
    nodes      = list(mock_graph.nodes())
    node_index = {n: i for i, n in enumerate(nodes)}
    mat        = np.array([[0.0, 141.4], [141.4, 0.0]])
    return mat, node_index


@pytest.fixture
def components(mock_graph, node_positions, distance_matrix_and_index):
    mat, idx   = distance_matrix_and_index
    state      = SimulationState()
    ambulances = [Ambulance(id=1, start_node=1, graph=mock_graph)]
    # Set initial pixel position
    ambulances[0].pixel_pos = (100.0, 100.0)
    spawner    = EventSpawner(lambda_rate=0.0, node_positions=node_positions)
    
    # Sprint 7: TrafficModel
    from src.simulation.traffic import TrafficModel
    traffic = TrafficModel(mock_graph, node_positions)
    
    dispatcher = DispatcherBrain(
        ambulances      = ambulances,
        distance_matrix = mat,
        node_index      = idx,
        node_positions  = node_positions,
        graph           = mock_graph,
        traffic         = traffic,
        cfg             = {}
    )
    return state, ambulances, spawner, dispatcher, node_positions, traffic


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestTickBasics:
    def test_tick_increments_counter(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components
        _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)
        assert state.current_tick == 1

    def test_tick_updates_ambulance_positions(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components
        _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)
        assert 1 in state.ambulance_positions
        assert state.ambulance_positions[1] == (100.0, 100.0)

    def test_multiple_ticks_no_exception(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components
        for _ in range(50):
            _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)
        assert state.current_tick == 50


class TestDispatcherIntegration:
    def test_new_event_dispatched_in_tick(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components

        # Inject event before tick
        event = Accident(id=1, timestamp=0, location=2,
                         pixel_pos=(200, 200), priority=1)
        dispatcher.active_events.append(event)

        _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)

        assert event.assigned_ambulance_id == 1
        assert ambulances[0].state == AmbulanceState.IN_TRANSIT

    def test_dispatcher_owns_active_events(self, components):
        """active_events must be on dispatcher, not on SimulationState."""
        state, ambulances, spawner, dispatcher, node_pos, traffic = components
        # SimulationState no longer has active_events attribute
        assert not hasattr(state, "active_events")

    def test_scene_service_timer_completes_event(self, components):
        """After SCENE_SERVICE_TICKS ticks on-scene, ambulance returns to IDLE."""
        from src.config import SCENE_SERVICE_TICKS
        state, ambulances, spawner, dispatcher, node_pos, traffic = components

        event = Accident(id=1, timestamp=0, location=2,
                         pixel_pos=(200, 200), priority=1)
        dispatcher.active_events.append(event)

        # Run enough ticks for dispatch + travel + service
        for _ in range(SCENE_SERVICE_TICKS + 20):
            _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)

        assert ambulances[0].state == AmbulanceState.IDLE
        assert event.resolved is True


class TestMetricsIntegration:
    def test_art_positive_after_resolved_event(self, components):
        from src.config import SCENE_SERVICE_TICKS
        state, ambulances, spawner, dispatcher, node_pos, traffic = components

        event = Accident(id=1, timestamp=0, location=2,
                         pixel_pos=(200, 200), priority=1)
        dispatcher.active_events.append(event)

        for _ in range(SCENE_SERVICE_TICKS + 20):
            _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)

        assert dispatcher.metrics_tracker.art > 0

    def test_hud_data_has_required_keys(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components
        _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)
        hud = dispatcher.metrics_tracker.get_hud_data()
        for key in ("art", "total_events", "latest_rt", "min_rt", "max_rt"):
            assert key in hud


class TestDashedPath:
    def test_pixel_polyline_nonempty_while_in_transit(self, components):
        state, ambulances, spawner, dispatcher, node_pos, traffic = components

        event = Accident(id=1, timestamp=0, location=2,
                         pixel_pos=(200, 200), priority=1)
        dispatcher.active_events.append(event)
        _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)

        if ambulances[0].state == AmbulanceState.IN_TRANSIT:
            assert len(ambulances[0].pixel_polyline) > 0

    def test_pixel_polyline_cleared_after_completion(self, components):
        from src.config import SCENE_SERVICE_TICKS
        state, ambulances, spawner, dispatcher, node_pos, traffic = components

        event = Accident(id=1, timestamp=0, location=2,
                         pixel_pos=(200, 200), priority=1)
        dispatcher.active_events.append(event)

        for _ in range(SCENE_SERVICE_TICKS + 20):
            _tick(state, ambulances, spawner, dispatcher, node_pos, traffic, None)

        assert ambulances[0].pixel_polyline == []
