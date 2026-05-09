"""
run_sensitivity.py – Sprint 10 (US-037, US-038, US-039)

Batch runner for sensitivity analysis sweeps.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time

import numpy as np

# ── Headless env var MUST be set before any pygame-importing project module ────
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--headless", action="store_true")
_pre, _ = _parser.parse_known_args()
if _pre.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sim_config_loader import load_sim_config
from src.simulation.simulation_engine import load_graph, load_node_positions, _load_or_compute_matrix, SimulationEngine
from src.simulation.random_fleet import generate_random_fleet
import json

logger = logging.getLogger(__name__)

def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

class LambdaSweepRunner:
    def __init__(self, config: dict, graph, node_positions: dict,
                 distance_matrix, optimal_fleet: list[int]):
        self.config          = config
        self.graph           = graph
        self.node_positions  = node_positions
        self.distance_matrix = distance_matrix
        self.optimal_fleet   = optimal_fleet
        self.results: list[dict] = []

    def run(self) -> None:
        lambda_values = self.config["sweeps"]["lambda"]["values"]
        num_ambulances = self.config["sweeps"]["lambda"]["fixed_num_ambulances"]
        num_runs = self.config["simulation"]["num_runs_per_config"]

        print(f"\n[Sensitivity] Starting lambda sweep ({len(lambda_values) * 2 * num_runs} runs)...")
        for lam_idx, lam in enumerate(lambda_values):
            for fleet_type in ["baseline", "ai"]:
                run_arts = []
                run_events = []
                for run_id in range(num_runs):
                    fleet = self._get_fleet(fleet_type, num_ambulances, run_id)
                    seed  = self.config["seeds"]["event_seed"] + (lam_idx * 100) + run_id
                    art, total_events = self._single_run(fleet, lam, num_ambulances, seed)
                    run_arts.append(art)
                    run_events.append(total_events)

                self.results.append({
                    "lambda":       lam,
                    "fleet_type":   fleet_type,
                    "mean_art":     float(np.mean(run_arts)),
                    "std_art":      float(np.std(run_arts, ddof=1)) if len(run_arts) > 1 else 0.0,
                    "mean_events":  float(np.mean(run_events)),
                    "num_runs":     num_runs
                })
                print(f"  L={lam} | {fleet_type:8s} | ART={np.mean(run_arts):.2f} +/- "
                      f"{np.std(run_arts, ddof=1) if len(run_arts) > 1 else 0.0:.2f}")

    def _get_fleet(self, fleet_type: str, num_ambulances: int,
                   run_id: int) -> list[int]:
        if fleet_type == "ai":
            return self.optimal_fleet
        seed = self.config["seeds"]["random_seed"] + run_id
        # generate_random_fleet expects a config dict
        cfg = {"n_stations": num_ambulances, "n_repeats": 1}
        return generate_random_fleet(self.graph, cfg, seed=seed)[0]

    def _single_run(self, fleet, lambda_rate, num_ambulances, event_seed) -> tuple:
        engine = SimulationEngine(
            graph=self.graph, node_positions=self.node_positions,
            distance_matrix=self.distance_matrix,
            start_nodes=fleet, ticks=self.config["simulation"]["ticks"],
            lambda_rate=lambda_rate, event_seed=event_seed,
            ambulance_seed=self.config["seeds"]["ambulance_seed"],
            headless=True
        )
        engine.run()
        t = engine.metrics_tracker
        return t.art, len(t.response_times)

    def export_csv(self, path: str) -> None:
        _ensure_dir(path)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        print(f"[Sensitivity] Lambda sweep complete. CSV saved to {path}.")


class FleetSizeSweepRunner:
    def __init__(self, config: dict, graph, node_positions: dict,
                 distance_matrix, optimal_fleet: list[int]):
        self.config          = config
        self.graph           = graph
        self.node_positions  = node_positions
        self.distance_matrix = distance_matrix
        self.optimal_fleet   = optimal_fleet
        self.results: list[dict] = []

    def run(self) -> None:
        fleet_sizes = self.config["sweeps"]["fleet_size"]["values"]
        lambda_rate = self.config["sweeps"]["fleet_size"]["fixed_lambda"]
        num_runs    = self.config["simulation"]["num_runs_per_config"]

        print(f"\n[Sensitivity] Starting fleet size sweep ({len(fleet_sizes) * 2 * num_runs} runs)...")
        for size_idx, num_amb in enumerate(fleet_sizes):
            for fleet_type in ["baseline", "ai"]:
                run_arts = []
                for run_id in range(num_runs):
                    fleet = self._get_fleet(fleet_type, num_amb, run_id)
                    seed  = (self.config["seeds"]["event_seed"]
                             + 1000 + (size_idx * 100) + run_id)
                    art, _ = self._single_run(fleet, lambda_rate, num_amb, seed)
                    run_arts.append(art)

                self.results.append({
                    "num_ambulances": num_amb,
                    "fleet_type":     fleet_type,
                    "mean_art":       float(np.mean(run_arts)),
                    "std_art":        float(np.std(run_arts, ddof=1)) if len(run_arts) > 1 else 0.0,
                    "num_runs":       num_runs
                })
                print(f"  N={num_amb:2d} | {fleet_type:8s} | ART={np.mean(run_arts):.2f} +/- "
                      f"{np.std(run_arts, ddof=1) if len(run_arts) > 1 else 0.0:.2f}")

    def _get_fleet(self, fleet_type: str, num_ambulances: int,
                   run_id: int) -> list[int]:
        if fleet_type == "baseline":
            seed = self.config["seeds"]["random_seed"] + run_id
            cfg = {"n_stations": num_ambulances, "n_repeats": 1}
            return generate_random_fleet(self.graph, cfg, seed=seed)[0]
        
        if num_ambulances <= len(self.optimal_fleet):
            return self.optimal_fleet[:num_ambulances]
        else:
            extra_seed = self.config["seeds"]["random_seed"] + 1000 + run_id
            cfg = {"n_stations": num_ambulances - len(self.optimal_fleet), "n_repeats": 1}
            extra = generate_random_fleet(
                self.graph,
                cfg,
                seed=extra_seed
            )[0]
            return self.optimal_fleet + extra

    def _single_run(self, fleet, lambda_rate, num_ambulances, event_seed) -> tuple:
        engine = SimulationEngine(
            graph=self.graph, node_positions=self.node_positions,
            distance_matrix=self.distance_matrix,
            start_nodes=fleet, ticks=self.config["simulation"]["ticks"],
            lambda_rate=lambda_rate, event_seed=event_seed,
            ambulance_seed=self.config["seeds"]["ambulance_seed"],
            headless=True
        )
        engine.run()
        t = engine.metrics_tracker
        return t.art, len(t.response_times)

    def export_csv(self, path: str) -> None:
        _ensure_dir(path)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        print(f"[Sensitivity] Fleet sweep complete. CSV saved to {path}.")


class HDBSCANSweepRunner:
    def __init__(self, config: dict, graph, node_positions: dict,
                 distance_matrix, optimal_fleet: list[int]):
        self.config          = config
        self.graph           = graph
        self.node_positions  = node_positions
        self.distance_matrix = distance_matrix
        self.optimal_fleet   = optimal_fleet
        self.results: list[dict] = []

    def run(self) -> None:
        sweep_cfg = self.config["sweeps"]["hdbscan"]
        num_runs  = self.config["simulation"]["num_runs_per_config"]
        cell_idx  = 0
        total_cells = len(sweep_cfg["min_cluster_size_values"]) * len(sweep_cfg["min_samples_values"]) * len(sweep_cfg["update_interval_values"])

        print(f"\n[Sensitivity] Starting HDBSCAN sweep ({total_cells * num_runs} runs)...")
        for mcs in sweep_cfg["min_cluster_size_values"]:
            for ms in sweep_cfg["min_samples_values"]:
                for interval in sweep_cfg["update_interval_values"]:
                    run_arts, run_rebalances, run_clusters, run_noise = [], [], [], []

                    for run_id in range(num_runs):
                        seed = (self.config["seeds"]["event_seed"]
                                + 5000 + (cell_idx * 100) + run_id)
                        metrics = self._single_run(mcs, ms, interval, seed)
                        run_arts.append(metrics["art"])
                        run_rebalances.append(metrics["rebalance_count"])
                        run_clusters.append(metrics["mean_clusters"])
                        run_noise.append(metrics["noise_fraction"])

                    self.results.append({
                        "min_cluster_size":       mcs,
                        "min_samples":            ms,
                        "rebalance_interval":     interval,
                        "mean_art":               float(np.mean(run_arts)),
                        "std_art":                float(np.std(run_arts, ddof=1)) if len(run_arts) > 1 else 0.0,
                        "mean_rebalance_count":   float(np.mean(run_rebalances)),
                        "mean_clusters_detected": float(np.mean(run_clusters)),
                        "mean_noise_fraction":    float(np.mean(run_noise))
                    })
                    print(f"  mcs={mcs} ms={ms} interval={interval} | "
                          f"ART={np.mean(run_arts):.2f} | "
                          f"rebalances={np.mean(run_rebalances):.1f}")
                    cell_idx += 1

    def _single_run(self, min_cluster_size: int, min_samples: int,
                    rebalance_interval: int, event_seed: int) -> dict:
        engine = SimulationEngine(
            graph=self.graph, node_positions=self.node_positions,
            distance_matrix=self.distance_matrix,
            start_nodes=self.optimal_fleet,
            ticks=self.config["simulation"]["ticks"],
            lambda_rate=self.config["sweeps"]["hdbscan"]["fixed_lambda"],
            event_seed=event_seed,
            ambulance_seed=self.config["seeds"]["ambulance_seed"],
            hdbscan_min_cluster_size=min_cluster_size,
            hdbscan_min_samples=min_samples,
            rebalance_interval=rebalance_interval,
            headless=True
        )
        try:
            engine.run()
        except Exception as e:
            logger.error(f"Run failed for mcs={min_cluster_size}, ms={min_samples}: {e}")
            return {
                "art":              999.0,
                "rebalance_count":  0,
                "mean_clusters":    0.0,
                "noise_fraction":   1.0
            }
        
        t = engine.metrics_tracker
        d = engine.dispatcher
        return {
            "art":              t.art,
            "rebalance_count":  d.rebalance_count,
            "mean_clusters":    d.mean_clusters_per_rebalance,
            "noise_fraction":   d.mean_noise_fraction
        }

    def export_csv(self, path: str) -> None:
        _ensure_dir(path)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
        print(f"[Sensitivity] HDBSCAN sweep complete. CSV saved to {path}.")


def main():
    parser = argparse.ArgumentParser(description="ResQ-Graph Sensitivity Sweep")
    parser.add_argument("--config", default="headless_sensitivity.yaml")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    import yaml
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    start_time = time.time()
    
    # Common map loading
    graph = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")
    
    # Try to load traffic-aware matrix first if it exists (Sprint 9)
    if os.path.exists("data/traffic_distance_matrix.npy"):
        distance_matrix, _ = _load_or_compute_matrix(graph, "data/traffic_distance_matrix.npy")
    else:
        distance_matrix, _ = _load_or_compute_matrix(graph)

    with open("outputs/optimal_stations.json", "r") as f:
        optimal_fleet = [int(n) for n in json.load(f)["optimal_stations"]]

    # --- Sweep 1: Lambda ---
    ls = LambdaSweepRunner(config, graph, node_positions, distance_matrix, optimal_fleet)
    ls.run()
    ls.export_csv(config["output"]["sensitivity_dir"] + "lambda_sweep.csv")

    # --- Sweep 2: Fleet Size ---
    fs = FleetSizeSweepRunner(config, graph, node_positions, distance_matrix, optimal_fleet)
    fs.run()
    fs.export_csv(config["output"]["sensitivity_dir"] + "fleet_sweep.csv")

    # --- Sweep 3: HDBSCAN ---
    hs = HDBSCANSweepRunner(config, graph, node_positions, distance_matrix, optimal_fleet)
    hs.run()
    hs.export_csv(config["output"]["sensitivity_dir"] + "hdbscan_sweep.csv")

    elapsed_minutes = (time.time() - start_time) / 60.0
    print(f"\n[Sensitivity] Total wall time: {elapsed_minutes:.1f} minutes")

if __name__ == "__main__":
    main()
