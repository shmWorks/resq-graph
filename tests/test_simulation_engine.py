"""
test_simulation_engine.py – Sprint 10 (US-037)

Integration tests for the SimulationEngine class and programmatic control.
"""
import pytest
import numpy as np
import networkx as nx

from src.simulation.simulation_engine import SimulationEngine, SimulationState
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import EventSpawner, Accident

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
def distance_matrix(mock_graph):
    # Very simple matrix for 2 nodes
    return np.array([[0.0, 141.4], [141.4, 0.0]])

def test_engine_init(mock_graph, node_positions, distance_matrix):
    engine = SimulationEngine(
        graph=mock_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[1],
        ticks=100,
        headless=True
    )
    assert len(engine.ambulances) == 1
    assert engine.state.current_tick == 0
    assert engine.state.lambda_rate == 0.05

def test_engine_tick_updates_state(mock_graph, node_positions, distance_matrix):
    engine = SimulationEngine(
        graph=mock_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[1],
        ticks=100,
        headless=True
    )
    engine._tick()
    assert engine.state.current_tick == 1
    assert 0 in engine.state.ambulance_positions

def test_engine_add_ambulance(mock_graph, node_positions, distance_matrix):
    engine = SimulationEngine(
        graph=mock_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[1],
        ticks=100,
        headless=True
    )
    engine.add_ambulance(2)
    assert len(engine.ambulances) == 2
    assert engine.ambulances[1].id == 1 # 0 was first, 1 is second
    assert engine.ambulances[1].current_location == 2
    assert len(engine.dispatcher.ambulances) == 2

def test_engine_run_completes(mock_graph, node_positions, distance_matrix):
    # Set lambda to 0 for a predictable 10-tick run
    engine = SimulationEngine(
        graph=mock_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[1],
        ticks=10,
        lambda_rate=0.0,
        headless=True
    )
    state, metrics, dispatcher = engine.run()
    assert state.current_tick == 10
    assert len(metrics.response_times) == 0
