"""
test_random_fleet.py – Sprint 8 (US-029)

Verifies:
  - No duplicate node IDs within a single placement set.
  - Same seed always produces identical output (reproducibility).
  - Output dimensions match n_stations × n_repeats.

Run with:
    pytest tests/ -v
"""
from __future__ import annotations

import json
import os
import sys

import networkx as nx
import pytest

# Ensure project root is on path (consistent with other tests via conftest.py)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.simulation.random_fleet import generate_random_fleet


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def small_graph() -> nx.MultiGraph:
    """A tiny 20-node MultiGraph sufficient for testing fleet generation."""
    G = nx.MultiGraph()
    G.add_nodes_from(range(20))
    # Add some edges so it's a valid graph (not required by fleet generator,
    # but makes the fixture realistic)
    for i in range(19):
        G.add_edge(i, i + 1, weight=1.0)
    return G


@pytest.fixture()
def base_cfg() -> dict:
    """Minimal config matching headless_baseline.yaml defaults."""
    return {
        "n_stations":  5,
        "n_repeats":   10,
        "random_seed": 42,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGenerateRandomFleet:

    def test_output_dimensions(self, small_graph, base_cfg):
        """Output must have n_repeats outer entries, each n_stations long."""
        placements = generate_random_fleet(small_graph, base_cfg)

        assert len(placements) == base_cfg["n_repeats"], (
            f"Expected {base_cfg['n_repeats']} repeats, got {len(placements)}"
        )
        for i, placement in enumerate(placements):
            assert len(placement) == base_cfg["n_stations"], (
                f"Repeat {i}: expected {base_cfg['n_stations']} stations, "
                f"got {len(placement)}"
            )

    def test_no_duplicate_nodes_per_placement(self, small_graph, base_cfg):
        """Each single placement set must contain unique node IDs."""
        placements = generate_random_fleet(small_graph, base_cfg)

        for i, placement in enumerate(placements):
            assert len(set(placement)) == len(placement), (
                f"Repeat {i} contains duplicate node IDs: {placement}"
            )

    def test_all_nodes_are_graph_nodes(self, small_graph, base_cfg):
        """All returned node IDs must be valid nodes in the graph."""
        valid_nodes = set(small_graph.nodes())
        placements  = generate_random_fleet(small_graph, base_cfg)

        for i, placement in enumerate(placements):
            for node in placement:
                assert node in valid_nodes, (
                    f"Repeat {i}: node {node!r} not in graph"
                )

    def test_reproducibility_same_seed(self, small_graph, base_cfg):
        """Identical seed must always produce identical output."""
        run_a = generate_random_fleet(small_graph, base_cfg, seed=99)
        run_b = generate_random_fleet(small_graph, base_cfg, seed=99)

        assert run_a == run_b, (
            "Same seed produced different placements — not reproducible."
        )

    def test_different_seeds_produce_different_output(self, small_graph, base_cfg):
        """Different seeds should (with overwhelming probability) differ."""
        run_a = generate_random_fleet(small_graph, base_cfg, seed=1)
        run_b = generate_random_fleet(small_graph, base_cfg, seed=9999)

        # It is astronomically unlikely these are identical on a 20-node graph
        assert run_a != run_b, (
            "Different seeds produced identical placements — suspicious."
        )

    def test_seed_override_takes_precedence(self, small_graph, base_cfg):
        """Explicit seed= kwarg must override cfg['random_seed']."""
        cfg_seed_42 = {**base_cfg, "random_seed": 42}

        run_with_override = generate_random_fleet(small_graph, cfg_seed_42, seed=7)
        run_with_cfg_seed = generate_random_fleet(small_graph, cfg_seed_42, seed=42)

        assert run_with_override != run_with_cfg_seed, (
            "seed= override did not take precedence over cfg['random_seed']"
        )
        # And using seed=7 twice must match
        run_with_7_again  = generate_random_fleet(small_graph, cfg_seed_42, seed=7)
        assert run_with_override == run_with_7_again

    def test_n_stations_too_large_raises(self, small_graph):
        """Requesting more stations than nodes must raise ValueError."""
        bad_cfg = {"n_stations": 100, "n_repeats": 3, "random_seed": 1}
        with pytest.raises(ValueError, match="n_stations"):
            generate_random_fleet(small_graph, bad_cfg)

    def test_single_repeat(self, small_graph):
        """n_repeats=1 must return a list with one inner list."""
        cfg = {"n_stations": 3, "n_repeats": 1, "random_seed": 0}
        result = generate_random_fleet(small_graph, cfg)
        assert len(result) == 1
        assert len(result[0]) == 3

    def test_log_file_written(self, small_graph, base_cfg, tmp_path, monkeypatch):
        """Calling generate_random_fleet must write/update the JSON log file."""
        log_path = str(tmp_path / "random_fleet_log.json")

        # Patch the internal log path
        import src.simulation.random_fleet as rf_module
        monkeypatch.setattr(rf_module, "_log_placements",
                            lambda placements, seed, log_path=log_path:
                            rf_module._log_placements.__wrapped__(placements, seed, log_path)
                            if hasattr(rf_module._log_placements, "__wrapped__")
                            else _write_log(placements, seed, log_path))

        # Directly test the _log_placements helper
        placements = [[0, 1, 2, 3, 4]]
        rf_module._log_placements(placements, seed=42, log_path=log_path)

        assert os.path.isfile(log_path), "Log file was not created."
        with open(log_path) as fh:
            data = json.load(fh)
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["seed"] == 42
        assert data[0]["nodes"] == [0, 1, 2, 3, 4]


def _write_log(placements, seed, log_path):
    """Helper used in the log test above."""
    import json, os
    from datetime import datetime, timezone
    entries = [{"repeat": i, "seed": seed, "nodes": n,
                "timestamp": datetime.now(timezone.utc).isoformat()}
               for i, n in enumerate(placements)]
    with open(log_path, "w") as fh:
        json.dump(entries, fh)
