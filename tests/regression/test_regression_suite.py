"""
test_regression_suite.py – Sprint 11 (US-044)
Compares current simulation performance against established baselines.
"""
import json
import os
import pytest
import numpy as np
import networkx as nx
from src.simulation.simulation_engine import SimulationEngine

def build_stable_graph():
    G = nx.MultiGraph()
    G.add_nodes_from([0, 1, 2, 3])
    for n in G.nodes():
        G.nodes[n].update({'x': 0, 'y': 0})
    G.add_edge(0, 1, weight=1, length=1)
    G.add_edge(1, 2, weight=1, length=1)
    G.add_edge(2, 3, weight=1, length=1)
    G.add_edge(3, 0, weight=1, length=1)
    return G

def test_simulation_performance_regression():
    # 1. Setup exact same environment as baseline
    graph = build_stable_graph()
    nodes = list(graph.nodes())
    node_positions = {0: (100, 100), 1: (200, 100), 2: (200, 200), 3: (100, 200)}
    distance_matrix = np.array([
        [0, 1, 2, 1],
        [1, 0, 1, 2],
        [2, 1, 0, 1],
        [1, 2, 1, 0]
    ])
    start_nodes = [0, 2]
    
    engine = SimulationEngine(
        graph=graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=100,
        lambda_rate=0.2,
        event_seed=42,
        ambulance_seed=42,
        headless=True
    )
    
    # 2. Run simulation
    engine.run()
    results = engine.metrics_tracker.get_hud_data()
    
    # 3. Load baseline
    baseline_path = os.path.join(os.path.dirname(__file__), "regression_baselines.json")
    with open(baseline_path, "r") as f:
        baselines = json.load(f)
    
    expected = baselines["baseline_100_ticks"]
    
    # 4. Assert no regression (within 1% tolerance for floats)
    assert results["total_events"] == expected["total_events"]
    assert results["art"] == pytest.approx(expected["art"], rel=0.01)
    assert results["min_rt"] == expected["min_rt"]
    assert results["max_rt"] == expected["max_rt"]
    assert results["std_dev"] == pytest.approx(expected["std_dev"], rel=0.01)
