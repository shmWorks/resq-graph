import sys
import os
import pytest
import networkx as nx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Enforce SDL dummy before any pygame import in any test file.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="session")
def model_town_graph():
    """
    Real model_town.graphml loaded once per test session.
    Use for integration and regression tests only — too large for unit tests.
    """
    G = nx.read_graphml("data/model_town.graphml")
    return nx.MultiGraph(G)


@pytest.fixture
def minimal_graph():
    """
    Tiny 4-node graph for unit tests. Predictable edge weights enable
    exact path assertions without loading the real map.
    """
    G = nx.MultiGraph()
    G.add_nodes_from([0, 1, 2, 3])
    # Give nodes x/y so heuristics work without KeyError
    # We use identical coordinates so haversine returns 0, making it
    # pure Dijkstra and avoiding heuristic overestimation with fake lengths.
    G.nodes[0].update({'x': 0, 'y': 0})
    G.nodes[1].update({'x': 0, 'y': 0})
    G.nodes[2].update({'x': 0, 'y': 0})
    G.nodes[3].update({'x': 0, 'y': 0})
    
    G.add_edge(0, 1, weight=1, length=1)
    G.add_edge(1, 2, weight=1, length=1)
    G.add_edge(2, 3, weight=1, length=1)
    G.add_edge(0, 3, weight=5, length=5)   # Longer direct edge — A* should prefer 0→1→2→3
    return G


@pytest.fixture
def base_config():
    """Minimal valid config dict for SimulationEngine construction."""
    return {
        "ticks": 100,
        "strategy": "ai",
        "num_ambulances": 3,
        "lambda_rate": 0.05,
        "min_cluster_size": 2,
        "rebalance_interval": 25,
        "coverage_radius_m": 500,
        "random_seed": 0,
        "event_seed": 0,
        "ambulance_seed": 0,
        "headless": True,
    }
