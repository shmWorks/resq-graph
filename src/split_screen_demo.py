"""
split_screen_demo.py – Sprint 9 (US-035)

Pygame split-screen demo: left panel runs the random baseline fleet,
right panel runs the GA-optimised AI fleet, both advancing tick-for-tick
with a shared tick counter displayed at the top.

Controls
--------
    ENTER / SPACE   Start / pause both simulations
    Q / ESC         Quit

Usage
-----
    python src/split_screen_demo.py
    python src/split_screen_demo.py --headless   # for CI / testing
"""
from __future__ import annotations

import argparse
import os
import sys

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--headless", action="store_true")
_pre, _ = _parser.parse_known_args()
if _pre.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import pygame

from src.sim_config_loader import load_sim_config
from src.simulation.simulation_engine import (
    load_graph,
    load_node_positions,
    _load_or_compute_matrix,
    SimulationState,
    _tick,
)
from src.simulation.ambulance import Ambulance
from src.simulation.event_spawner import EventSpawner
from src.simulation.dispatcher import DispatcherBrain
from src.simulation.traffic import TrafficModel
from src.simulation.sim_logger import setup_logging, SimLogBuffer
from src.simulation.random_fleet import generate_random_fleet
from src.rendering.pygame_renderer import PygameRenderer
from src.run_ai_fleet import load_optimal_fleet


# ── Layout constants ──────────────────────────────────────────────────────────
PANEL_W      = 900
PANEL_H      = 650
HEADER_H     = 60
DIVIDER_W    = 4
TOTAL_W      = PANEL_W * 2 + DIVIDER_W
TOTAL_H      = PANEL_H + HEADER_H

COLOUR_BG        = (10,  10,  20)
COLOUR_DIVIDER   = (50,  60,  80)
COLOUR_HEADER    = (15,  15,  30)
COLOUR_TEXT      = (226, 232, 240)
COLOUR_ACCENT_B  = (129, 140, 248)   # baseline – indigo
COLOUR_ACCENT_AI = (52,  211, 153)   # AI fleet – emerald
COLOUR_PAUSED    = (251, 191,  36)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ResQ-Graph Split-Screen Demo")
    p.add_argument("--headless",  action="store_true")
    p.add_argument("--config",    default="headless_ai.yaml")
    p.add_argument("--ticks",     type=int, default=1000)
    p.add_argument("--seed",      type=int, default=42,
                   help="Seed for random-fleet placement and events")
    return p.parse_args()


def _build_engine(
    cfg: dict,
    station_nodes: list[int],
    event_seed: int,
    graph,
    node_positions: dict,
    distance_matrix,
    node_index: dict,
) -> tuple[list[Ambulance], EventSpawner, DispatcherBrain, TrafficModel | None, SimulationState]:
    """Construct one simulation engine (ambulances, spawner, dispatcher)."""
    num_ambulances = int(cfg.get("NUM_AMBULANCES", 5))
    poisson_lambda = float(cfg.get("POISSON_LAMBDA", 0.05))

    start_nodes = station_nodes[:num_ambulances]
    while len(start_nodes) < num_ambulances:
        fallback = list(node_positions.keys())
        start_nodes.append(int(fallback[len(start_nodes) % len(fallback)]))

    ambulances = [
        Ambulance(id=i, start_node=start_nodes[i], graph=graph)
        for i in range(num_ambulances)
    ]
    for amb in ambulances:
        amb.update_position(node_positions)

    traffic: TrafficModel | None = None
    if cfg.get("TRAFFIC_ENABLED", True):
        traffic = TrafficModel(
            graph=graph,
            node_positions=node_positions,
            max_multiplier=float(cfg.get("CONGESTION_MAX_MULTIPLIER", 2.5)),
            decay_rate=float(cfg.get("CONGESTION_DECAY_RATE", 0.02)),
        )

    spawner = EventSpawner(
        lambda_rate=poisson_lambda,
        node_positions=node_positions,
        rng_seed=event_seed,
    )
    dispatcher = DispatcherBrain(
        ambulances=ambulances,
        distance_matrix=distance_matrix,
        node_index=node_index,
        node_positions=node_positions,
        graph=graph,
        traffic=traffic,
        cfg=cfg,
    )
    state = SimulationState()
    return ambulances, spawner, dispatcher, traffic, state


def _draw_header(
    screen: pygame.Surface,
    font_large,
    font_small,
    tick: int,
    max_ticks: int,
    paused: bool,
    b_art: float,
    ai_art: float,
) -> None:
    pygame.draw.rect(screen, COLOUR_HEADER, (0, 0, TOTAL_W, HEADER_H))
    pygame.draw.line(screen, COLOUR_DIVIDER, (0, HEADER_H), (TOTAL_W, HEADER_H), 2)

    # Centre tick counter
    status = "  [PAUSED]" if paused else ""
    tick_surf = font_large.render(f"Tick {tick} / {max_ticks}{status}", True,
                                  COLOUR_PAUSED if paused else COLOUR_TEXT)
    screen.blit(tick_surf, tick_surf.get_rect(center=(TOTAL_W // 2, HEADER_H // 2)))

    # Left label
    b_surf = font_small.render(
        f"RANDOM BASELINE   ART={b_art:.1f}", True, COLOUR_ACCENT_B)
    screen.blit(b_surf, (20, HEADER_H // 2 - b_surf.get_height() // 2))

    # Right label
    ai_surf = font_small.render(
        f"AI OPTIMISED FLEET   ART={ai_art:.1f}", True, COLOUR_ACCENT_AI)
    screen.blit(ai_surf, (PANEL_W + DIVIDER_W + 20,
                           HEADER_H // 2 - ai_surf.get_height() // 2))


def _running_art(dispatcher) -> float:
    rt = dispatcher.metrics_tracker.response_times
    return (sum(rt) / len(rt)) if rt else 0.0


def main() -> None:
    args = _parse_args()

    try:
        cfg = load_sim_config(path=args.config)
    except FileNotFoundError:
        cfg = {}

    setup_logging(level=cfg.get("LOG_LEVEL", "WARNING"),
                  log_file=cfg.get("LOG_FILE", "outputs/split_screen.log"))

    max_ticks    = args.ticks
    event_seed   = int(cfg.get("event_seed", args.seed))
    headless     = _pre.headless

    pygame.init()
    pygame.display.set_caption("ResQ-Graph — Split-Screen Demo")
    screen = pygame.display.set_mode((TOTAL_W, TOTAL_H))
    clock  = pygame.time.Clock()

    font_large = pygame.font.SysFont("monospace", 20, bold=True)
    font_small = pygame.font.SysFont("monospace", 16)

    # ── Shared map data ────────────────────────────────────────────────────
    graph          = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")
    distance_matrix, node_index = _load_or_compute_matrix(graph)

    # ── Station nodes ──────────────────────────────────────────────────────
    random_placements = generate_random_fleet(graph, cfg, seed=args.seed)
    baseline_nodes    = random_placements[0]

    optimal_path  = cfg.get("optimal_stations_path", "outputs/optimal_stations.json")
    ai_nodes      = load_optimal_fleet(optimal_path)

    # ── Build two independent engines ──────────────────────────────────────
    b_ambs, b_spawner, b_disp, b_traffic, b_state = _build_engine(
        cfg, baseline_nodes, event_seed,
        graph, node_positions, distance_matrix, node_index,
    )
    a_ambs, a_spawner, a_disp, a_traffic, a_state = _build_engine(
        cfg, ai_nodes, event_seed,
        graph, node_positions, distance_matrix, node_index,
    )

    # ── Two surfaces for split-screen rendering ────────────────────────────
    b_surf  = pygame.Surface((PANEL_W, PANEL_H))
    ai_surf = pygame.Surface((PANEL_W, PANEL_H))

    b_renderer  = PygameRenderer(b_surf,  node_positions)
    ai_renderer = PygameRenderer(ai_surf, node_positions)

    log_buf = SimLogBuffer(capacity=50)
    log_buf.attach()

    # ── Main loop ──────────────────────────────────────────────────────────
    running = True
    started = headless   # in headless mode start immediately
    paused  = False

    print("\n[Demo] Split-screen loaded. Press ENTER to start.")

    # Clear any residual events (e.g. the ENTER key that triggered the transition)
    pygame.event.clear()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    started = True
                    paused  = False
                elif event.key == pygame.K_SPACE:
                    if started:
                        paused = not paused
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False

        if started and not paused:
            if b_state.current_tick < max_ticks:
                _tick(b_state, b_ambs, b_spawner, b_disp, node_positions, b_traffic, None)
            if a_state.current_tick < max_ticks:
                _tick(a_state, a_ambs, a_spawner, a_disp, node_positions, a_traffic, None)

            if b_state.current_tick >= max_ticks and a_state.current_tick >= max_ticks:
                running = False

        if not headless:
            screen.fill(COLOUR_BG)

            # Draw each panel
            for renderer, state, ambs, disp, surf in [
                (b_renderer,  b_state, b_ambs, b_disp,  b_surf),
                (ai_renderer, a_state, a_ambs, a_disp, ai_surf),
            ]:
                surf.fill(COLOUR_BG)
                renderer.draw(
                    state=state,
                    ambulances=ambs,
                    dispatcher=disp,
                    show_metrics_panel=False,
                    show_hotspots=False,
                    show_traffic=False,
                    show_log=False,
                    log_buffer=log_buf,
                    current_tick=state.current_tick,
                )

            screen.blit(b_surf,  (0,            HEADER_H))
            screen.blit(ai_surf, (PANEL_W + DIVIDER_W, HEADER_H))
            pygame.draw.rect(screen, COLOUR_DIVIDER,
                             (PANEL_W, HEADER_H, DIVIDER_W, PANEL_H))

            _draw_header(
                screen, font_large, font_small,
                b_state.current_tick, max_ticks, paused,
                _running_art(b_disp), _running_art(a_disp),
            )

            if not started:
                overlay = font_large.render(
                    "Press ENTER to start the comparison demo", True, COLOUR_PAUSED)
                screen.blit(overlay, overlay.get_rect(
                    center=(TOTAL_W // 2, TOTAL_H // 2)))

            pygame.display.flip()
            clock.tick(30)
        else:
            # Headless: run to completion without rendering
            if not running:
                break

    # ── Final stats ────────────────────────────────────────────────────────
    b_final  = _running_art(b_disp)
    ai_final = _running_art(a_disp)
    print(f"\n[Demo] Baseline ART  = {b_final:.2f} ticks")
    print(f"[Demo] AI fleet ART  = {ai_final:.2f} ticks")
    if b_final > 0:
        imp = (b_final - ai_final) / b_final * 100
        print(f"[Demo] Improvement   = {imp:+.1f}%")

    pygame.quit()


if __name__ == "__main__":
    main()
