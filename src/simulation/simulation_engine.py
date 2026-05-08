"""
simulation_engine.py – Sprint 6 & 7 (US-020, US-023, US-025, US-026, US-027, US-028)

Wires all Sprint 6/7 subsystems into the main tick loop.

Sprint 6 changes
----------------
- H key toggles hotspot overlay.
- Dispatcher receives DemandClusterer results via rebalance_fleet().

Sprint 7 changes
----------------
- Config loaded from sim_config.yaml via sim_config_loader (US-027).
- --profile CLI argument selects a YAML profile (e.g. --profile headless).
- Logging initialised via setup_logging() + SimLogBuffer (US-028).
- TrafficModel integrated; traffic.update() called every tick (US-025).
- Renderer's traffic cache invalidated after each traffic.update() call.
- T key toggles traffic overlay; L key toggles full log history (US-028).
- Headless mode: SDL_VIDEODRIVER=dummy set before pygame.init() when
  profile sets TARGET_FPS: 0 (headless profile).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

import networkx as nx
import json
import numpy as np
import pygame

from src.sim_config_loader import load_sim_config
from src.simulation.sim_logger import setup_logging, SimLogBuffer
from src.config import (
    NUM_AMBULANCES,
    SIMULATION_TICKS,
    TARGET_FPS,
    REDRAW_INTERVAL,
    POISSON_LAMBDA,
    METRICS_FLUSH_INTERVAL,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident, EventSpawner
from src.simulation.dispatcher import DispatcherBrain
from src.simulation.traffic import TrafficModel
from src.distance_matrix import compute_distance_matrix, load_distance_matrix
from src.rendering.pygame_renderer import PygameRenderer

logger = logging.getLogger(__name__)


# ── Simulation State ───────────────────────────────────────────────────────────

@dataclass
class SimulationState:
    """Lightweight snapshot of simulation progress."""
    current_tick:        int              = 0
    ambulance_positions: dict[int, tuple] = field(default_factory=dict)
    paused:              bool             = False


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_node_positions(filepath: str) -> dict:
    with open(filepath, "r") as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items()}


def load_graph(filepath: str):
    G = nx.read_graphml(filepath)
    G_undirected = nx.MultiGraph(G)
    return nx.relabel_nodes(G_undirected, {n: int(n) for n in G_undirected.nodes()})


def _build_node_index(graph) -> dict:
    return {node: i for i, node in enumerate(graph.nodes())}


def _load_or_compute_matrix(graph, matrix_path: str = "data/distance_matrix.npy"):
    node_index = _build_node_index(graph)
    if os.path.exists(matrix_path):
        logger.info("Loading distance matrix from %s ...", matrix_path)
        matrix = load_distance_matrix(matrix_path)
    else:
        logger.info("Distance matrix not found. Computing ... (this may take a moment)")
        matrix, node_index = compute_distance_matrix(graph, save_path=matrix_path)
    return matrix, node_index


# ── Tick logic ─────────────────────────────────────────────────────────────────

def _tick(
    state:          SimulationState,
    ambulances:     list[Ambulance],
    spawner:        EventSpawner,
    dispatcher:     DispatcherBrain,
    node_positions: dict,
    traffic:        TrafficModel | None,
    renderer:       PygameRenderer | None,
) -> None:
    """One simulation tick (Sprint 6/7).

    Tick order
    ----------
    1. Update ambulance positions.
    2. Spawn new events.
    3. Update traffic model (decay + build).
    4. Invalidate renderer traffic cache.
    5. Dispatcher tick.
    6. Update state snapshot.
    """
    # Step 1: move ambulances
    for amb in ambulances:
        amb.update_position(node_positions)

    # Step 2: spawn
    new_accidents = spawner.spawn(state.current_tick)

    # Step 3: traffic update
    if traffic is not None:
        traffic.update(dispatcher.active_events + new_accidents, state.current_tick)
        # Step 4: invalidate cached heatmap surface
        if renderer is not None:
            renderer.invalidate_traffic_cache()

    # Step 5: dispatcher
    dispatcher.tick(new_accidents, state.current_tick)

    # Step 6: bookkeeping
    state.ambulance_positions = {a.id: a.pixel_pos for a in ambulances}
    state.current_tick += 1


# ── CLI argument parsing ───────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ResQ-Graph EMS Dispatcher Simulation"
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="YAML config profile to use (e.g. 'headless', 'high_stress').",
    )
    parser.add_argument(
        "--config",
        default="sim_config.yaml",
        help="Path to the YAML config file (default: sim_config.yaml).",
    )
    return parser.parse_known_args()[0]


# ── Main entry point ───────────────────────────────────────────────────────────

def run_simulation(
    cfg_override: dict | None = None,
    initial_nodes: list[int] | None = None,
) -> None:
    """Initialise all components and run the main Pygame loop.

    Parameters
    ----------
    cfg_override : dict, optional
        When supplied (e.g. by run_baseline.py) this dict is used directly as
        the runtime config, bypassing CLI argument parsing and YAML loading.
    initial_nodes : list[int], optional
        When supplied, these node IDs are used as ambulance start positions
        instead of the default modulo-based selection.  Must have exactly
        ``num_ambulances`` entries.
    """
    # ── When called programmatically, skip CLI parsing ─────────────────────
    if cfg_override is not None:
        cfg = cfg_override
    else:
        args = _parse_args()
        # ── Load YAML config ───────────────────────────────────────────────
        try:
            cfg = load_sim_config(path=args.config, profile=args.profile)
        except (FileNotFoundError, KeyError) as exc:
            # Graceful fallback: use hard-coded defaults
            logging.basicConfig(level=logging.WARNING)
            logging.warning("Config load failed (%s); using hard-coded defaults.", exc)
            cfg = {}

    # ── Initialise logging (US-028) ────────────────────────────────────────
    log_level = cfg.get("LOG_LEVEL", "INFO")
    log_file  = cfg.get("LOG_FILE",  "outputs/sim.log")
    setup_logging(level=log_level, log_file=log_file)

    log_buffer = SimLogBuffer(capacity=200)
    log_buffer.attach()   # intercept all log records into in-memory buffer

    # ── Runtime parameters (YAML overrides hard-coded config.py) ──────────
    num_ambulances    = int(cfg.get("NUM_AMBULANCES",    NUM_AMBULANCES))
    simulation_ticks  = int(cfg.get("SIMULATION_TICKS",  SIMULATION_TICKS))
    target_fps        = int(cfg.get("TARGET_FPS",         TARGET_FPS))
    poisson_lambda    = float(cfg.get("POISSON_LAMBDA",   POISSON_LAMBDA))
    screen_w          = int(cfg.get("SCREEN_W",           WINDOW_WIDTH))
    screen_h          = int(cfg.get("SCREEN_H",           WINDOW_HEIGHT))

    # ── Headless mode (US-027): set dummy video driver BEFORE pygame.init()
    headless = (target_fps == 0)
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        logger.info("Headless mode: SDL_VIDEODRIVER=dummy")

    pygame.init()
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("ResQ-Graph – Dispatcher Simulation")
    clock = pygame.time.Clock()

    # ── Load map data ──────────────────────────────────────────────────────
    node_positions = load_node_positions("data/node_positions.json")
    graph          = load_graph("data/model_town.graphml")

    # ── Build / load distance matrix ──────────────────────────────────────
    distance_matrix, node_index = _load_or_compute_matrix(graph)

    # ── Initialise ambulances ──────────────────────────────────────────────
    # initial_nodes can be injected by run_baseline.py (US-030)
    if initial_nodes is not None:
        start_nodes = initial_nodes[:num_ambulances]
        # Pad with defaults if fewer nodes than ambulances provided
        if len(start_nodes) < num_ambulances:
            fallback = list(node_positions.keys())
            while len(start_nodes) < num_ambulances:
                start_nodes.append(int(fallback[len(start_nodes) % len(fallback)]))
    else:
        node_ids    = list(node_positions.keys())
        start_nodes = [int(node_ids[i % len(node_ids)]) for i in range(num_ambulances)]

    ambulances = [
        Ambulance(id=i, start_node=start_nodes[i], graph=graph)
        for i in range(num_ambulances)
    ]
    for amb in ambulances:
        amb.update_position(node_positions)

    # ── Traffic model (US-025) ─────────────────────────────────────────────
    traffic_enabled = cfg.get("TRAFFIC_ENABLED", True)
    traffic: TrafficModel | None = None
    if traffic_enabled:
        traffic = TrafficModel(
            graph            = graph,
            node_positions   = node_positions,
            max_multiplier   = float(cfg.get("CONGESTION_MAX_MULTIPLIER", 2.5)),
            decay_rate       = float(cfg.get("CONGESTION_DECAY_RATE",     0.02)),
        )
        logger.info("Traffic model initialised (max_mult=%.1f).", traffic.max_multiplier)

    # ── Initialise subsystems ──────────────────────────────────────────────
    event_seed = cfg.get("event_seed", None)  # US-032: reproducibility seed
    spawner    = EventSpawner(lambda_rate=poisson_lambda, node_positions=node_positions, rng_seed=event_seed)
    dispatcher = DispatcherBrain(
        ambulances      = ambulances,
        distance_matrix = distance_matrix,
        node_index      = node_index,
        node_positions  = node_positions,
        graph           = graph,
        traffic         = traffic,
        cfg             = cfg,
    )
    renderer = PygameRenderer(screen, node_positions)
    state    = SimulationState()

    # ── Toggle states ──────────────────────────────────────────────────────
    show_metrics_panel = False
    show_hotspots      = False
    show_traffic       = False
    show_log           = False
    running            = True

    _profile_label = getattr(args, "profile", None) if cfg_override is None else "programmatic"
    logger.info(
        "Simulation starting: %d ambulances, %d ticks, profile=%r.",
        num_ambulances, simulation_ticks, _profile_label,
    )

    # ── Main loop ──────────────────────────────────────────────────────────
    while running and state.current_tick < simulation_ticks:

        # Handle Pygame events
        for pg_event in pygame.event.get():
            if pg_event.type == pygame.QUIT:
                running = False
            elif pg_event.type == pygame.KEYDOWN:
                if pg_event.key == pygame.K_SPACE:
                    state.paused = not state.paused
                elif pg_event.key == pygame.K_m:
                    show_metrics_panel = not show_metrics_panel
                elif pg_event.key == pygame.K_h:        # Sprint 6 US-024
                    show_hotspots = not show_hotspots
                elif pg_event.key == pygame.K_t:        # Sprint 7 US-025
                    show_traffic  = not show_traffic
                elif pg_event.key == pygame.K_l:        # Sprint 7 US-028
                    show_log      = not show_log

        # Simulation tick (skipped while paused)
        if not state.paused:
            _tick(
                state, ambulances, spawner, dispatcher,
                node_positions, traffic,
                renderer if not headless else None,
            )

        # Render (skip rendering in headless mode)
        if not headless and state.current_tick % REDRAW_INTERVAL == 0:
            renderer.draw(
                state          = state,
                ambulances     = ambulances,
                dispatcher     = dispatcher,
                show_metrics_panel = show_metrics_panel,
                show_hotspots  = show_hotspots,
                show_traffic   = show_traffic,
                show_log       = show_log,
                log_buffer     = log_buffer,
                current_tick   = state.current_tick,
            )

        if not headless:
            clock.tick(target_fps if target_fps > 0 else 0)

    # ── Cleanup ────────────────────────────────────────────────────────────
    logger.info("Simulation ended at tick %d.", state.current_tick)
    dispatcher.metrics_tracker.flush_csv()
    dispatcher.metrics_tracker.export_summary_csv()
    pygame.quit()
