"""
run_baseline.py – Sprint 8 (US-030)

Batch baseline runner. Executes the simulation headlessly N times using
random ambulance station placements, collects ART per run via MetricsTracker,
and writes outputs/baseline_results.csv.

Usage
-----
    python src/run_baseline.py --headless --config headless_baseline.yaml

Flags
-----
    --headless         Set SDL_VIDEODRIVER=dummy (must precede any pygame init)
    --config PATH      YAML config file (default: headless_baseline.yaml)
    --ticks N          Override ticks_per_run from config
    --seeds N [N ...]  Override the per-run seeds (space-separated integers)
"""
from __future__ import annotations

import argparse
import csv
import logging
import math
import os
import sys

# ── Headless env var MUST be set before any pygame-importing project module ────
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--headless", action="store_true")
_pre, _ = _parser.parse_known_args()
if _pre.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

# ── Now safe to import project modules ────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sim_config_loader import load_sim_config                      # noqa: E402
from src.simulation.random_fleet import generate_random_fleet          # noqa: E402
from src.simulation.simulation_engine import (                         # noqa: E402
    load_graph,
    load_node_positions,
    run_simulation,
)
from src.simulation.sim_logger import setup_logging                    # noqa: E402

logger = logging.getLogger(__name__)

# ── Output path ───────────────────────────────────────────────────────────────
BASELINE_CSV = "outputs/baseline_results.csv"
_FIELDS = ["run_id", "seed", "n_events", "mean_art", "std_art", "ticks"]


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ResQ-Graph Sprint 8 Baseline Runner")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--config",   default="headless_baseline.yaml")
    p.add_argument("--ticks",    type=int,   default=None,
                   help="Override ticks_per_run from config.")
    p.add_argument("--seeds",    type=int,   nargs="+", default=None,
                   help="Explicit list of per-run seeds (overrides n_repeats).")
    return p.parse_args()


# ── Per-run metrics extraction ─────────────────────────────────────────────────

def _run_stats(metrics_tracker) -> tuple[float, float]:
    """Return (mean_art, std_art) from a MetricsTracker after one run."""
    rt = metrics_tracker.response_times
    if not rt:
        return 0.0, 0.0
    mean = sum(rt) / len(rt)
    std  = math.sqrt(sum((x - mean) ** 2 for x in rt) / len(rt))
    return round(mean, 3), round(std, 3)


# ── CSV writer ────────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], summary: dict) -> None:
    os.makedirs(os.path.dirname(BASELINE_CSV), exist_ok=True)
    with open(BASELINE_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(summary)
    logger.info("Baseline results written -> %s", BASELINE_CSV)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    # Load config via the established loader (US-032: all seeds from YAML)
    cfg = load_sim_config(path=args.config)

    setup_logging(level=cfg.get("LOG_LEVEL", "WARNING"),
                  log_file=cfg.get("LOG_FILE", "outputs/baseline_sim.log"))

    ticks_per_run: int = args.ticks or int(cfg.get("ticks_per_run", 1000))
    n_repeats:     int = int(cfg.get("n_repeats", 10))
    base_seed:     int = int(cfg.get("random_seed", 42))

    # Build per-run seeds: base_seed, base_seed+1, ..., base_seed+(n-1)
    if args.seeds:
        run_seeds = args.seeds
    else:
        run_seeds = [base_seed + i for i in range(n_repeats)]

    # Load graph once — it's an nx.MultiGraph and is not mutated per run
    graph          = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")

    logger.info(
        "Starting baseline: %d runs x %d ticks (seeds: %s ... %s)",
        len(run_seeds), ticks_per_run, run_seeds[0], run_seeds[-1],
    )
    print(f"\n[Baseline] Starting {len(run_seeds)} headless runs x {ticks_per_run} ticks each ...\n")

    rows: list[dict] = []

    for run_id, seed in enumerate(run_seeds):
        # Generate one random fleet placement for this run's seed
        placements   = generate_random_fleet(graph, cfg, seed=seed)
        start_nodes  = placements[0]   # one placement per run

        # Build a per-run config with the correct tick count and event seed
        run_cfg = dict(cfg)
        run_cfg["SIMULATION_TICKS"] = ticks_per_run
        run_cfg["TARGET_FPS"]       = 0            # headless
        run_cfg["event_seed"]       = seed         # reproducible events per run

        # Run headlessly — run_simulation returns after all ticks complete
        run_simulation(cfg_override=run_cfg, initial_nodes=start_nodes)

        # Collect metrics from the freshly-flushed summary CSV
        # MetricsTracker.export_summary_csv() is called at end of run_simulation
        # For cross-run aggregation we use the in-memory response_times captured
        # during this run. Since run_simulation creates a fresh MetricsTracker,
        # we re-derive stats from the per-event CSV it just wrote.
        mean_art, std_art, n_events = _read_last_run_stats()

        row = {
            "run_id":   run_id,
            "seed":     seed,
            "n_events": n_events,
            "mean_art": mean_art,
            "std_art":  std_art,
            "ticks":    ticks_per_run,
        }
        rows.append(row)
        print(f"  Run {run_id:>2d} | seed={seed} | events={n_events:>4d} | "
              f"ART={mean_art:>7.2f} +/- {std_art:.2f}")

    # ── Summary row ───────────────────────────────────────────────────────────
    valid = [r for r in rows if r["n_events"] > 0]
    if valid:
        all_arts = [r["mean_art"] for r in valid]
        grand_mean = round(sum(all_arts) / len(all_arts), 3)
        grand_std  = round(
            math.sqrt(sum((x - grand_mean) ** 2 for x in all_arts) / len(all_arts)), 3
        )
    else:
        grand_mean = grand_std = 0.0

    summary = {
        "run_id":   "SUMMARY",
        "seed":     "all",
        "n_events": sum(r["n_events"] for r in rows),
        "mean_art": grand_mean,
        "std_art":  grand_std,
        "ticks":    ticks_per_run * len(run_seeds),
    }

    _write_csv(rows, summary)
    print(f"\n[Baseline] Done. Grand mean ART = {grand_mean} +/- {grand_std}")
    print(f"[Baseline] Results -> {BASELINE_CSV}\n")


def _read_last_run_stats() -> tuple[float, float, int]:
    """Read ART stats from the last-written metrics_summary.csv."""
    summary_path = "outputs/metrics_summary.csv"
    if not os.path.isfile(summary_path):
        return 0.0, 0.0, 0
    try:
        with open(summary_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                return (
                    float(row.get("art",        0)),
                    float(row.get("std_dev",     0)),
                    int(row.get("total_events", 0)),
                )
    except (OSError, KeyError, ValueError):
        pass
    return 0.0, 0.0, 0


if __name__ == "__main__":
    main()
