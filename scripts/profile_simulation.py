"""
scripts/profile_simulation.py – Sprint 12 (US-045)

Runs a 1000-tick headless simulation under cProfile and dumps:
  - outputs/profile_1000_ticks.prof  (for snakeviz / gprof2dot)
  - Top 30 functions by cumulative time printed to stdout

Usage:
    python scripts/profile_simulation.py
    snakeviz outputs/profile_1000_ticks.prof   # optional visual explorer
"""
import cProfile
import io
import os
import pstats
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.simulation.simulation_engine import (
    SimulationEngine, load_graph, load_node_positions, _load_or_compute_matrix,
)


def _run():
    graph     = load_graph("data/model_town.graphml")
    positions = load_node_positions("data/node_positions.json")
    matrix, _ = _load_or_compute_matrix(graph)
    nodes     = list(positions.keys())

    engine = SimulationEngine(
        graph=graph,
        node_positions=positions,
        distance_matrix=matrix,
        start_nodes=nodes[:5],
        ticks=1000,
        lambda_rate=0.1,
        event_seed=42,
        ambulance_seed=42,
        headless=True,
    )
    engine.run()
    print(f"\n[Profile] Final ART: {engine.metrics_tracker.art:.2f} ticks "
          f"| Events: {len(engine.metrics_tracker.response_times)}")


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    _run()
    profiler.disable()

    # ── Print top 30 by cumulative time ──────────────────────────────────────
    stream = io.StringIO()
    stats  = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(30)
    print(stream.getvalue())

    # ── Save .prof file ───────────────────────────────────────────────────────
    os.makedirs("outputs", exist_ok=True)
    prof_path = "outputs/profile_1000_ticks.prof"
    profiler.dump_stats(prof_path)
    print(f"[Profile] Saved to {prof_path}")
    print(f"[Profile] View with: snakeviz {prof_path}")
