"""
random_fleet.py – Sprint 8 (US-029)

Generates random ambulance station placements from the road network graph.
Used as a control group for baseline comparison against the optimized fleet.

All parameters are read from the config dict produced by sim_config_loader.py.
Logging uses the existing sim_logger infrastructure (no separate logger setup).
"""
from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def generate_random_fleet(
    graph,
    cfg: dict[str, Any],
    seed: int | None = None,
) -> list[list[int]]:
    """Generate N random station placements from the graph.

    Parameters
    ----------
    graph : nx.MultiGraph
        The loaded road network. Nodes are already int-typed (as loaded by
        simulation_engine.load_graph).
    cfg : dict
        Config dict from sim_config_loader. Keys consumed:
            - ``n_stations``  (int, default 5)
            - ``n_repeats``   (int, default 10)
            - ``random_seed`` (int, default 42) — overridden by *seed* if given
    seed : int, optional
        Explicit seed override. When supplied it takes precedence over
        ``cfg["random_seed"]``. Used by the baseline runner to vary seeds
        across runs while keeping the base config unchanged.

    Returns
    -------
    list[list[int]]
        Outer list has ``n_repeats`` entries; each inner list contains
        ``n_stations`` unique node IDs.
    """
    n_stations: int = int(cfg.get("n_stations", 5))
    n_repeats:  int = int(cfg.get("n_repeats",  10))
    base_seed:  int = int(cfg.get("random_seed", 42))

    effective_seed = seed if seed is not None else base_seed

    all_nodes = list(graph.nodes())
    if n_stations > len(all_nodes):
        raise ValueError(
            f"n_stations={n_stations} exceeds graph size ({len(all_nodes)} nodes)."
        )

    rng = random.Random(effective_seed)
    placements: list[list[int]] = []

    for i in range(n_repeats):
        chosen = rng.sample(all_nodes, n_stations)
        placements.append([int(n) for n in chosen])
        logger.debug(
            "Random fleet repeat %d/%d (seed=%d): %s",
            i + 1, n_repeats, effective_seed, chosen,
        )

    _log_placements(placements, effective_seed)
    return placements


# ── Internal helpers ───────────────────────────────────────────────────────────

def _log_placements(
    placements: list[list[int]],
    seed: int,
    log_path: str = "outputs/random_fleet_log.json",
) -> None:
    """Append each placement set to a JSON log for full reproducibility."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    entries = [
        {
            "repeat":    i,
            "seed":      seed,
            "nodes":     nodes,
            "timestamp": timestamp,
        }
        for i, nodes in enumerate(placements)
    ]

    # Read existing log (if any) and append
    existing: list[dict] = []
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.extend(entries)

    try:
        with open(log_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
        logger.info(
            "Random fleet log updated → %s (%d total entries).",
            log_path, len(existing),
        )
    except OSError as exc:
        logger.warning("Could not write random fleet log: %s", exc)
