"""
test_empty_graph.py – Sprint 11 (US-043)
Edge case: gracefully handling an empty or single-node graph.
"""
import pytest
import networkx as nx
from src.simulation.simulation_engine import SimulationEngine

def test_single_node_graph(base_config):
    # A graph with 0 edges and 1 node
    graph = nx.MultiGraph()
    graph.add_node(0)
    
    import numpy as np
    distance_matrix = np.zeros((1, 1))
    node_positions = {0: (0, 0)}
    start_nodes = [0]
    
    engine = SimulationEngine(
        graph=graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=10,
        headless=True
    )
    
    # Run should not crash despite no edges to route across
    engine.run()
    assert engine.state.current_tick == 10
