import pytest
import os
import yaml
import networkx as nx
import numpy as np
from src.run_sensitivity import LambdaSweepRunner, FleetSizeSweepRunner, HDBSCANSweepRunner

@pytest.fixture
def mock_setup():
    graph = nx.MultiGraph()
    graph.add_node(1, x=0.0, y=0.0)
    graph.add_node(2, x=1.0, y=1.0)
    graph.add_edge(1, 2, weight=1.0)
    pos = {1: (0, 0), 2: (100, 100)}
    dist = np.array([[0, 1], [1, 0]])
    config = {
        "simulation": {"ticks": 10, "num_runs_per_config": 1},
        "seeds": {"event_seed": 42, "ambulance_seed": 0, "random_seed": 99},
        "sweeps": {
            "lambda": {"values": [0.05], "fixed_num_ambulances": 1},
            "fleet_size": {"values": [1], "fixed_lambda": 0.05},
            "hdbscan": {
                "min_cluster_size_values": [5],
                "min_samples_values": [3],
                "update_interval_values": [50],
                "fixed_lambda": 0.05,
                "fixed_num_ambulances": 1
            }
        }
    }
    fleet = [1]
    return config, graph, pos, dist, fleet

def test_lambda_sweep_runner(mock_setup):
    config, graph, pos, dist, fleet = mock_setup
    runner = LambdaSweepRunner(config, graph, pos, dist, fleet)
    runner.run()
    assert len(runner.results) == 2 # 1 value * 2 fleet types
    assert "mean_art" in runner.results[0]

def test_fleet_size_sweep_runner(mock_setup):
    config, graph, pos, dist, fleet = mock_setup
    runner = FleetSizeSweepRunner(config, graph, pos, dist, fleet)
    runner.run()
    assert len(runner.results) == 2 # 1 value * 2 fleet types
    assert "num_ambulances" in runner.results[0]

def test_hdbscan_sweep_runner(mock_setup):
    config, graph, pos, dist, fleet = mock_setup
    runner = HDBSCANSweepRunner(config, graph, pos, dist, fleet)
    runner.run()
    assert len(runner.results) == 1 # 1x1x1 combination
    assert "mean_noise_fraction" in runner.results[0]
