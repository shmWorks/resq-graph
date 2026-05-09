"""
tests/integration/test_scaling.py – Sprint 12 (US-048)

Validates that the simulation engine scales to 10,000+ ticks with 10+
ambulances and completes in under 10 minutes headless.

Marked @pytest.mark.slow — excluded from CI by default.
Run locally: pytest tests/integration/test_scaling.py -v -s
"""
import time
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.mark.slow
def test_10k_ticks_10_ambulances():
    """
    10,000 ticks with 10 ambulances must:
    - Complete without exception
    - Finish in < 10 minutes (600s)
    - Produce at least 1 resolved event (λ=0.1 over 10K ticks will generate many)
    """
    from src.simulation.simulation_engine import (
        SimulationEngine, load_graph, load_node_positions, _load_or_compute_matrix,
    )

    graph     = load_graph("data/model_town.graphml")
    positions = load_node_positions("data/node_positions.json")
    matrix, _ = _load_or_compute_matrix(graph)
    nodes     = list(positions.keys())

    engine = SimulationEngine(
        graph=graph,
        node_positions=positions,
        distance_matrix=matrix,
        start_nodes=nodes[:10],     # 10 ambulances
        ticks=10_000,
        lambda_rate=0.1,
        event_seed=42,
        ambulance_seed=42,
        headless=True,
    )

    t0 = time.perf_counter()
    engine.run()
    elapsed = time.perf_counter() - t0

    print(f"\n[Scaling] 10K ticks completed in {elapsed:.1f}s "
          f"({elapsed/60:.2f} min)")
    print(f"[Scaling] Events resolved: {len(engine.metrics_tracker.response_times)}")
    print(f"[Scaling] ART: {engine.metrics_tracker.art:.2f} ticks")

    assert engine.state.current_tick == 10_000, (
        f"Expected 10,000 ticks but engine stopped at {engine.state.current_tick}"
    )
    assert elapsed < 600, (
        f"10K-tick run took {elapsed:.0f}s, exceeds 10-minute limit"
    )
    assert len(engine.metrics_tracker.response_times) > 0, (
        "No events were resolved in 10,000 ticks with λ=0.1"
    )
