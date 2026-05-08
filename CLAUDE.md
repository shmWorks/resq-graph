# CLAUDE.md

Claude Code guidance for this repo.

## Project Overview

ResQ-Graph: agent-based emergency ambulance dispatch simulation. Ambulances navigate city road network (graph) to respond to dynamic emergencies. System optimizes response times via smart dispatch, dynamic fleet rebalancing, traffic models.

## Common Commands

```bash
# Run simulation (visual mode)
python src/main.py

# Run headless (no display)
python src/main.py --headless

# Run baseline batch experiment (Sprint 8)
python src/run_baseline.py --headless --config headless_baseline.yaml

# Run test suite
pytest tests/ -v

# Run specific test file
pytest tests/test_assignment.py -v
```

## Architecture

Tick-based engine (`src/simulation/simulation_engine.py`) orchestrates subsystems:

- **Map & Pathfinding**: Road network from `data/model_town.graphml` → `nx.MultiGraph` (undirected, prevents dead-end trap). A* uses Haversine heuristic. Pre-computed distance matrix (`data/distance_matrix.npy`) enables O(1) ambulance-event assignment.

- **Traffic Model**: Dynamic edge congestion from local event density. Modifies edge weights, triggers mid-route reroute when conditions worsen.

- **Dispatcher**: Owns active event queue. Assigns idle ambulances via distance matrix lookups. Coordinates periodic fleet rebalancing to hotspots.

- **Intelligence**: Custom HDBSCAN detects demand hotspots from active event locations. Clusters → proactive ambulance positioning.

- **Event Spawner**: Poisson distribution generates emergencies at random graph nodes.

- **Ambulance Agents**: State machines: IDLE → IN_TRANSIT → ON_SCENE → REBALANCING. Follow pre-calculated paths node-by-node, interpolate pixel positions for rendering.

## Key Design Decisions

- **Distance Matrix**: Never bypass `assignment.py` for proximity. Always use distance matrix for O(1) lookups. Fall back to Euclidean only if explicitly necessary.

- **Rendering**: `pygame_renderer.py` draws only data passed to `draw()`. Never mutate simulation state inside renderer.

- **Seeds**: All randomness flows through `sim_config_loader.py`. Zero hardcoded seeds. Use `event_seed`, `random_seed`, `ambulance_seed` from config.

- **Headless Mode**: Set `SDL_VIDEODRIVER=dummy` BEFORE any `pygame` import. Enforced in `main.py` and `run_baseline.py`.

- **HDBSCAN**: Custom impl in `src/intelligence/hdbscan.py`. Uses Excess of Mass formula `(birth_level - death_level) * size` for cluster stability.

## Current Sprint

Sprint 8 complete. Headless baseline runner, random fleet placement generator, baseline analysis tools with matplotlib visualizations.