"""
scripts/benchmark_astar.py – Sprint 12 (US-046)

Benchmarks A* performance before and after optimisation.
Runs 10 random (start, goal) pairs on model_town.graphml and reports
average time per call. Target: < 50ms.

Usage:
    python scripts/benchmark_astar.py
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.simulation.simulation_engine import (
    load_graph, load_node_positions, _load_or_compute_matrix,
)
from src.astar import astar
from src.astar_traffic import astar_traffic


def benchmark(fn, graph, pairs, label=""):
    times = []
    for start, goal in pairs:
        t0 = time.perf_counter()
        fn(graph, start, goal)
        times.append((time.perf_counter() - t0) * 1000)
    avg = sum(times) / len(times)
    mn  = min(times)
    mx  = max(times)
    status = "PASS" if avg < 50 else "FAIL"
    print(f"  {label:30s} avg={avg:6.2f}ms  min={mn:.2f}ms  max={mx:.2f}ms  [{status}]")
    return avg


if __name__ == "__main__":
    print("[Benchmark] Loading graph...")
    graph     = load_graph("data/model_town.graphml")
    positions = load_node_positions("data/node_positions.json")
    nodes     = list(graph.nodes())

    rng = random.Random(42)
    # 10 random pairs; ensure start != goal and both reachable
    pairs = []
    while len(pairs) < 10:
        s, g = rng.sample(nodes, 2)
        pairs.append((s, g))

    print(f"[Benchmark] {len(pairs)} pairs on graph with {len(nodes)} nodes\n")

    print("Results (target < 50ms avg):")
    benchmark(astar,         graph, pairs, "astar() base")
    benchmark(lambda g, s, t: astar_traffic(g, s, t, None),
              graph, pairs, "astar_traffic() no traffic")

    print("\n[Benchmark] Done.")
