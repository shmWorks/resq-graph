"""
main.py – Sprint 8 (US-030)

Entry point for the interactive (windowed) simulation.
Adds --headless and --config CLI flags. SDL_VIDEODRIVER=dummy is set
BEFORE any pygame import so the headless flag takes effect correctly.
"""
import argparse
import os
import sys

# ── Parse CLI FIRST, before any project imports that may pull in pygame ───────
_parser = argparse.ArgumentParser(description="ResQ-Graph EMS Dispatcher Simulation")
_parser.add_argument(
    "--headless",
    action="store_true",
    help="Run without a display window (SDL_VIDEODRIVER=dummy).",
)
_parser.add_argument(
    "--config",
    default="sim_config.yaml",
    help="Path to the YAML config file (default: sim_config.yaml).",
)
_parser.add_argument(
    "--profile",
    default=None,
    help="Named profile to activate from the YAML config.",
)
_args, _unknown = _parser.parse_known_args()

# ── Set headless env var BEFORE pygame is imported anywhere downstream ─────────
if _args.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

# ── Now it is safe to import project modules (which pull in pygame) ────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.simulation.simulation_engine import run_simulation  # noqa: E402

if __name__ == "__main__":
    try:
        state, _, _ = run_simulation()
        if state and getattr(state, "transition_to_demo", False):
            # Safe local import to avoid circular dependencies
            from src.split_screen_demo import main as demo_main
            demo_main()
    except KeyboardInterrupt:
        pass
