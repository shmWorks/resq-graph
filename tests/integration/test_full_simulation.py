"""
test_full_simulation.py – Sprint 11 (US-042)
Integration test for full SimulationEngine run.
"""
import pytest
from src.simulation.simulation_engine import SimulationEngine

def test_full_simulation_runs_to_completion(base_config, minimal_graph):
    import numpy as np
    nodes = list(minimal_graph.nodes())
    node_positions = {n: (0,0) for n in nodes}
    distance_matrix = np.zeros((4, 4))
    start_nodes = [0, 1]
    
    engine = SimulationEngine(
        graph=minimal_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=100,
        headless=True
    )
    engine.run()
    
    # Should complete 100 ticks without error
    assert engine.state.current_tick == 100
    assert len(engine.dispatcher.metrics_tracker.response_times) >= 0
