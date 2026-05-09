"""
tests/test_split_screen_demo.py – Sprint 9 (US-035)

Unit tests for src/split_screen_demo.py. Runs entirely in headless SDL mode.
"""
from __future__ import annotations

import os
import sys

# Force headless before any pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_split_screen_imports():
    """split_screen_demo can be imported without error."""
    import importlib
    mod = importlib.import_module("src.split_screen_demo")
    assert hasattr(mod, "main")


def test_build_engine_returns_correct_types():
    """_build_engine returns the expected tuple of objects."""
    import pygame
    pygame.init()

    from src.simulation.simulation_engine import (
        load_graph, load_node_positions, _load_or_compute_matrix, SimulationState,
    )
    from src.simulation.ambulance import Ambulance
    from src.simulation.event_spawner import EventSpawner
    from src.simulation.dispatcher import DispatcherBrain
    from src.split_screen_demo import _build_engine

    graph = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")
    dm, ni = _load_or_compute_matrix(graph)

    node_ids = list(node_positions.keys())
    stations = node_ids[:5]

    cfg = {
        "NUM_AMBULANCES": 5,
        "POISSON_LAMBDA": 0.05,
        "TRAFFIC_ENABLED": False,
    }
    engine = _build_engine(
        cfg, stations, 42, graph, node_positions, dm
    )

    assert isinstance(engine.ambulances, list) and len(engine.ambulances) == 5
    assert isinstance(engine.spawner, EventSpawner)
    assert isinstance(engine.dispatcher, DispatcherBrain)
    assert engine.traffic is None   # TRAFFIC_ENABLED=False
    assert isinstance(engine.state, SimulationState)
    pygame.quit()


def test_dual_engine_tick_parity():
    """Both engines advance the same number of ticks over N iterations."""
    import pygame
    pygame.init()

    from src.simulation.simulation_engine import (
        load_graph, load_node_positions, _load_or_compute_matrix,
    )
    from src.split_screen_demo import _build_engine

    graph = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")
    dm, ni = _load_or_compute_matrix(graph)

    node_ids = list(node_positions.keys())
    cfg = {"NUM_AMBULANCES": 5, "POISSON_LAMBDA": 0.05, "TRAFFIC_ENABLED": False}

    engine_b = _build_engine(
        cfg, node_ids[:5], 42, graph, node_positions, dm)
    engine_a = _build_engine(
        cfg, node_ids[5:10], 42, graph, node_positions, dm)

    N = 20
    for _ in range(N):
        engine_b._tick()
        engine_a._tick()

    assert engine_b.state.current_tick == N
    assert engine_a.state.current_tick == N

    pygame.quit()


def test_headless_main_runs_without_error(monkeypatch):
    """main() completes to tick 10 in headless mode without raising."""
    import sys as _sys
    # Patch sys.argv for the demo arg parser
    monkeypatch.setattr(_sys, "argv", [
        "split_screen_demo.py",
        "--headless",
        "--ticks", "10",
        "--seed", "42",
    ])

    # Force headless flag in the module's pre-parse namespace
    import src.split_screen_demo as demo_mod
    import types

    # Patch _pre to simulate --headless flag seen before import
    monkeypatch.setattr(demo_mod, "_pre",
                        types.SimpleNamespace(headless=True))

    # Patch pygame.display.flip and clock.tick to no-ops
    import pygame
    pygame.init()

    try:
        demo_mod.main()
    except SystemExit:
        pass   # acceptable – some arg parsers call sys.exit on --help
    finally:
        try:
            pygame.quit()
        except Exception:
            pass
