"""
test_unreachable_node.py – Sprint 11 (US-043)
Edge case: gracefully handling routing to a completely disconnected node.
"""
import pytest
import networkx as nx
import numpy as np
from src.simulation.simulation_engine import SimulationEngine
from src.simulation.event_spawner import Accident

def test_unreachable_node_handling():
    # Graph with two disconnected components: 0-1 and 2
    graph = nx.MultiGraph()
    graph.add_nodes_from([0, 1, 2])
    graph.add_edge(0, 1, weight=1.0)
    
    # distance matrix with inf for unreachable nodes
    distance_matrix = np.array([
        [0.0, 1.0, np.inf],
        [1.0, 0.0, np.inf],
        [np.inf, np.inf, 0.0]
    ])
    
    node_positions = {0: (0,0), 1: (1,1), 2: (2,2)}
    
    # Ambulance on node 0, event on node 2
    engine = SimulationEngine(
        graph=graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[0],
        ticks=10,
        headless=True
    )
    
    # In tick 1, we spawn an event at node 2
    event = Accident(id=1, timestamp=1, location=2, pixel_pos=(2,2), priority=1)
    engine.dispatcher.tick([event], current_tick=1)
    
    # Event should be completely ignored or remain unassigned (-1) without crashing
    assert event.assigned_ambulance_id == -1
    # Check that it's dropped from active events if completely unreachable,
    # or kept in active events with assigned_ambulance_id == -1
    assert event not in engine.dispatcher.active_events
