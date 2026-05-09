"""
simulation_engine.py – Sprint 10 refactor

Encapsulates the simulation logic in a SimulationEngine class for programmatic
control (US-037).
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
    transition_to_demo:  bool             = False
    lambda_rate:         float            = 0.05
    last_hdbscan_tick:   int              = 0


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


class SimulationEngine:
    """
    Programmatic interface for the ResQ-Graph simulation (Sprint 10).
    """
    def __init__(self, graph, node_positions, distance_matrix, start_nodes,
                 ticks=1000, lambda_rate=0.05, event_seed=None,
                 ambulance_seed=None, headless=True, screen_w=1200, screen_h=900,
                 hdbscan_min_cluster_size=5, hdbscan_min_samples=3,
                 rebalance_interval=50, cfg=None, target_fps=30):
        
        self.graph = graph
        self.node_positions = node_positions
        self.distance_matrix = distance_matrix
        self.start_nodes = start_nodes
        self.ticks = ticks
        self.lambda_rate = lambda_rate
        self.event_seed = event_seed
        self.ambulance_seed = ambulance_seed
        self.headless = headless
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.target_fps = target_fps if not headless else 0
        self.cfg = cfg or {}

        # Subsystems
        self.ambulances = [
            Ambulance(id=i, start_node=start_nodes[i], graph=graph)
            for i in range(len(start_nodes))
        ]
        for amb in self.ambulances:
            amb.update_position(node_positions)

        self.traffic = None
        if self.cfg.get("TRAFFIC_ENABLED", True):
            self.traffic = TrafficModel(
                graph=graph, node_positions=node_positions,
                max_multiplier=float(self.cfg.get("CONGESTION_MAX_MULTIPLIER", 2.5)),
                decay_rate=float(self.cfg.get("CONGESTION_DECAY_RATE", 0.02))
            )

        self.spawner = EventSpawner(lambda_rate=lambda_rate, 
                                    node_positions=node_positions, 
                                    rng_seed=event_seed)
        
        node_index = _build_node_index(graph)
        self.dispatcher = DispatcherBrain(
            ambulances=self.ambulances,
            distance_matrix=distance_matrix,
            node_index=node_index,
            node_positions=node_positions,
            graph=graph,
            traffic=self.traffic,
            cfg=self.cfg,
            hdbscan_min_cluster_size=hdbscan_min_cluster_size,
            hdbscan_min_samples=hdbscan_min_samples,
            rebalance_interval=rebalance_interval,
        )
        self.metrics_tracker = self.dispatcher.metrics_tracker
        
        self.state = SimulationState(lambda_rate=lambda_rate)
        self.renderer = None
        self.screen = None
        self.clock = None
        # US-048: reuse this dict each tick instead of creating a new one
        self._amb_pos_cache: dict = {a.id: a.pixel_pos for a in self.ambulances}

    def _init_pygame(self):
        if self.headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption("ResQ-Graph – Dispatcher Simulation")
        self.clock = pygame.time.Clock()
        self.renderer = PygameRenderer(self.screen, self.node_positions)

    def run(self):
        self._init_pygame()
        
        running = True
        show_metrics_panel = False
        show_hotspots = False
        show_traffic = False
        show_log = False
        
        # US-048: scale log buffer capacity for long runs to limit memory
        buffer_capacity = 50 if self.ticks > 5000 else 200
        log_buffer = SimLogBuffer(capacity=buffer_capacity)
        log_buffer.attach()

        while running and self.state.current_tick < self.ticks:
            # Events
            for pg_event in pygame.event.get():
                if pg_event.type == pygame.QUIT:
                    running = False
                elif pg_event.type == pygame.KEYDOWN:
                    if pg_event.key == pygame.K_SPACE:
                        self.state.paused = not self.state.paused
                    elif pg_event.key == pygame.K_m:
                        show_metrics_panel = not show_metrics_panel
                    elif pg_event.key == pygame.K_h:
                        show_hotspots = not show_hotspots
                    elif pg_event.key == pygame.K_t:
                        show_traffic = not show_traffic
                    elif pg_event.key == pygame.K_l:
                        show_log = not show_log
                    elif pg_event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        running = False
                        self.state.transition_to_demo = True
                    elif pg_event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        self.state.lambda_rate = min(self.state.lambda_rate + 0.01, 0.30)
                        self.spawner.set_lambda(self.state.lambda_rate)
                    elif pg_event.key == pygame.K_MINUS:
                        self.state.lambda_rate = max(self.state.lambda_rate - 0.01, 0.001)
                        self.spawner.set_lambda(self.state.lambda_rate)
                    elif pg_event.key == pygame.K_a:
                        new_node = int(list(self.node_positions.keys())[0]) # Placeholder
                        self.add_ambulance(new_node)
                    elif pg_event.key == pygame.K_k:
                        self.dispatcher.rebalance_fleet(self.state.current_tick)
                        self.state.last_hdbscan_tick = self.state.current_tick

            # Tick
            if not self.state.paused:
                self._tick()

            # Render
            if not self.headless and self.state.current_tick % REDRAW_INTERVAL == 0:
                self.renderer.draw(
                    state=self.state,
                    ambulances=self.ambulances,
                    dispatcher=self.dispatcher,
                    show_metrics_panel=show_metrics_panel,
                    show_hotspots=show_hotspots,
                    show_traffic=show_traffic,
                    show_log=show_log,
                    log_buffer=log_buffer,
                    current_tick=self.state.current_tick
                )
                pygame.display.flip()
                self.clock.tick(self.target_fps)

        self.metrics_tracker.flush_csv()
        self.metrics_tracker.export_summary_csv()
        pygame.quit()
        return self.state, self.metrics_tracker, self.dispatcher

    def _tick(self):
        for amb in self.ambulances:
            amb.update_position(self.node_positions)

        new_accidents = self.spawner.spawn(self.state.current_tick)

        if self.traffic is not None:
            self.traffic.update(self.dispatcher.active_events + new_accidents, self.state.current_tick)
            # US-047: only invalidate traffic cache every 5 ticks — congestion changes slowly
            if self.renderer and self.state.current_tick % 5 == 0:
                self.renderer.invalidate_traffic_cache()

        self.dispatcher.tick(new_accidents, self.state.current_tick)

        # US-048: mutate existing dict instead of creating a new one per tick
        for a in self.ambulances:
            self._amb_pos_cache[a.id] = a.pixel_pos
        self.state.ambulance_positions = self._amb_pos_cache
        self.state.current_tick += 1

    def add_ambulance(self, start_node: int):
        new_id = max(a.id for a in self.ambulances) + 1 if self.ambulances else 0
        amb = Ambulance(id=new_id, start_node=start_node, graph=self.graph)
        amb.update_position(self.node_positions)
        self.ambulances.append(amb)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ResQ-Graph EMS Dispatcher Simulation")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--config", default="sim_config.yaml")
    return parser.parse_known_args()[0]


def run_simulation(
    cfg_override: dict | None = None,
    initial_nodes: list[int] | None = None,
    hdbscan_min_cluster_size: int = 5,
    hdbscan_min_samples: int = 3,
    rebalance_interval: int = 50,
) -> tuple:
    if cfg_override is not None:
        cfg = cfg_override
    else:
        args = _parse_args()
        cfg = load_sim_config(path=args.config, profile=args.profile)

    setup_logging(level=cfg.get("LOG_LEVEL", "INFO"), log_file=cfg.get("LOG_FILE", "outputs/sim.log"))
    
    num_ambulances = int(cfg.get("NUM_AMBULANCES", NUM_AMBULANCES))
    node_positions = load_node_positions("data/node_positions.json")
    graph = load_graph("data/model_town.graphml")
    distance_matrix, _ = _load_or_compute_matrix(graph)

    if initial_nodes is not None:
        start_nodes = initial_nodes[:num_ambulances]
    else:
        node_ids = list(node_positions.keys())
        start_nodes = [int(node_ids[i % len(node_ids)]) for i in range(num_ambulances)]

    engine = SimulationEngine(
        graph=graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=int(cfg.get("SIMULATION_TICKS", SIMULATION_TICKS)),
        lambda_rate=float(cfg.get("POISSON_LAMBDA", POISSON_LAMBDA)),
        event_seed=cfg.get("event_seed"),
        headless=(int(cfg.get("TARGET_FPS", TARGET_FPS)) == 0),
        screen_w=int(cfg.get("SCREEN_W", WINDOW_WIDTH)),
        screen_h=int(cfg.get("SCREEN_H", WINDOW_HEIGHT)),
        hdbscan_min_cluster_size=hdbscan_min_cluster_size,
        hdbscan_min_samples=hdbscan_min_samples,
        rebalance_interval=rebalance_interval,
        cfg=cfg,
        target_fps=int(cfg.get("TARGET_FPS", TARGET_FPS))
    )
    
    return engine.run()
