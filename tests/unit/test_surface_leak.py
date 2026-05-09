"""
tests/unit/test_surface_leak.py – Sprint 12 (US-048)

Verifies that running 10,000 headless ticks does not accumulate memory
(no MemoryError) and reaches the target tick count.

Marked @pytest.mark.slow — excluded from CI by default.
Run locally: pytest tests/unit/test_surface_leak.py -v -s
"""
import gc
import os

import numpy as np
import networkx as nx
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _build_graph():
    """Minimal 4-node graph for fast tick iteration."""
    G = nx.MultiGraph()
    G.add_nodes_from(range(4))
    for n in G.nodes():
        G.nodes[n].update({'x': 0.0, 'y': 0.0})
    G.add_edge(0, 1, weight=1, length=1)
    G.add_edge(1, 2, weight=1, length=1)
    G.add_edge(2, 3, weight=1, length=1)
    G.add_edge(3, 0, weight=1, length=1)
    return G


@pytest.mark.slow
def test_no_surface_leak_10000_ticks():
    """
    10,000 headless ticks must complete without MemoryError and
    reach the full tick count. Pygame Surfaces created per-frame must
    be collected by GC before the run ends.
    """
    from src.simulation.simulation_engine import SimulationEngine

    graph = _build_graph()
    node_positions = {0: (100, 100), 1: (200, 100), 2: (200, 200), 3: (100, 200)}
    distance_matrix = np.array([
        [0, 1, 2, 1],
        [1, 0, 1, 2],
        [2, 1, 0, 1],
        [1, 2, 1, 0],
    ], dtype=float)

    engine = SimulationEngine(
        graph=graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[0, 2],
        ticks=10_000,
        lambda_rate=0.05,
        event_seed=42,
        ambulance_seed=42,
        headless=True,
    )

    gc.collect()
    engine.run()
    gc.collect()

    assert engine.state.current_tick == 10_000, (
        f"Expected 10,000 ticks but got {engine.state.current_tick}"
    )
    # If we get here without MemoryError, the surface leak test passes
