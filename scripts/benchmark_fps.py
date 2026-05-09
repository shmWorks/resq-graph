"""
scripts/benchmark_fps.py – Sprint 12 (US-047)

Runs 500 ticks with rendering enabled under SDL dummy driver
and measures average FPS. Target: >= 60 FPS.

Usage:
    python scripts/benchmark_fps.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.simulation.simulation_engine import (
    SimulationEngine, load_graph, load_node_positions, _load_or_compute_matrix,
)


if __name__ == "__main__":
    print("[FPS Benchmark] Loading graph...")
    graph     = load_graph("data/model_town.graphml")
    positions = load_node_positions("data/node_positions.json")
    matrix, _ = _load_or_compute_matrix(graph)
    nodes     = list(positions.keys())

    engine = SimulationEngine(
        graph=graph,
        node_positions=positions,
        distance_matrix=matrix,
        start_nodes=nodes[:10],   # 10 ambulances for worst-case sprite load
        ticks=500,
        lambda_rate=0.1,
        event_seed=42,
        ambulance_seed=42,
        headless=False,           # renderer active
        target_fps=0,             # uncapped FPS for max measurement
    )

    print("[FPS Benchmark] Running 500 ticks with renderer (SDL dummy)...")
    t0 = time.perf_counter()
    engine.run()
    elapsed = time.perf_counter() - t0

    ticks    = engine.state.current_tick
    avg_fps  = ticks / elapsed if elapsed > 0 else 0
    status   = "PASS" if avg_fps >= 60 else "FAIL"

    print(f"\n[FPS Benchmark] Ticks: {ticks} | Elapsed: {elapsed:.2f}s")
    print(f"[FPS Benchmark] Average FPS: {avg_fps:.1f}  (target >= 60)  {status}")
