# ResQ-Graph

ResQ-Graph is an agent-based graph simulation for emergency ambulance dispatch. It models a fleet of ambulances navigating a city road network (represented as a graph) to respond to dynamically generated emergency events. The project aims to simulate, visualize, and optimize response times using smart dispatch algorithms, dynamic fleet rebalancing, and realistic traffic models.

This repository is currently up-to-date through **Sprint 8**.

## Core Architecture & Components

The system relies on a central tick-based simulation engine that orchestrates several distinct sub-systems.

### 1. Simulation Engine (`src/simulation/simulation_engine.py`)
The heart of the project. It runs a `while` loop (capped at a defined number of ticks), updating the state of ambulances, spawning new events, updating traffic congestion, calling the dispatcher, and triggering the Pygame renderer. It ensures deterministic state updates.

### 2. Map & Pathfinding (`src/astar.py`, `src/distance_matrix.py`)
- **Map:** The road network is loaded from `data/model_town.graphml` (converted to an undirected MultiGraph to prevent dead-end trapping).
- **A\* Pathfinding:** `astar.py` calculates the shortest physical route for ambulances using a Haversine heuristic. 
- **Distance Matrix:** To avoid running A* for every single idle ambulance when a new event occurs, the system pre-computes an O(1) all-pairs shortest path distance matrix (`data/distance_matrix.npy`).

### 3. Traffic Model (`src/simulation/traffic.py`)
Introduced in Sprint 7, this model simulates dynamic edge congestion based on local event density and a base background level. It modifies the edge weights in the graph, affecting A* pathfinding and triggering mid-route rerouting if conditions worsen significantly (`CONGESTION_DETECTED`).

### 4. Dispatcher Brain (`src/simulation/dispatcher.py`, `src/simulation/assignment.py`)
Acts as the central command. It owns the queue of `active_events`. When a new emergency is ingested, it checks for idle ambulances and uses `assign_nearest_idle()` to find the closest one via the `distance_matrix`. It also coordinates periodic fleet rebalancing (sending idle ambulances to detected hotspots).

### 5. Intelligence & Clustering (`src/intelligence/`)
Uses a custom, from-scratch implementation of **HDBSCAN** (`hdbscan.py`) to detect demand hotspots from active event locations. The `DemandClusterer` groups events and finds optimal centroid nodes for proactive ambulance positioning (`REBALANCING`).

### 6. Event Spawner (`src/simulation/event_spawner.py`)
Simulates emergencies using a **Poisson distribution**. At each tick, it has a probability to spawn an `Accident` at a random node on the graph. 

### 7. Ambulance Agents (`src/simulation/ambulance.py`)
State machines that cycle between `IDLE`, `IN_TRANSIT`, `ON_SCENE`, and `REBALANCING`. They follow pre-calculated paths node-by-node, check for worsening traffic conditions to trigger rerouting, and interpolate their pixel positions between nodes for smooth rendering.

### 8. Metrics & Logging (`src/simulation/metrics_tracker.py`, `src/simulation/sim_logger.py`)
Logs response times (Spawn Tick → Arrival Tick) for every event. It provides real-time stats to the HUD, exports `metrics_events.csv` and `metrics_summary.csv` when the simulation ends, and maintains a comprehensive multi-level `sim.log`.

### 9. Visualization (`src/rendering/pygame_renderer.py`)
A highly optimized Pygame visualizer that renders:
- The static map background
-- Congestion heatmaps (Layered cached surface, `T` to toggle)
-- Hotspot pulsing circles and convex hulls (`H` to toggle)
-- Ambulance sprites (color-coded by state)
-- Emergency locations (Red Xs)
-- Dynamic dashed polylines representing active routes
-- A real-time HUD, a detailed metrics overlay (`M`), and a full log history (`L`)

---

## File Structure

```text
resq-graph/
├── data/
│   ├── model_town.graphml       # Road network map data
│   ├── node_positions.json      # Pre-calculated pixel coordinates for nodes
│   ├── map_bg.png               # Visual map background
│   └── distance_matrix.npy      # Precomputed distance matrix (auto-generated)
├── outputs/                     # Generated CSV metrics, logs, and baseline results go here
│   ├── figures/                 # Auto-generated matplotlib plots (Sprint 8)
│   ├── baseline_results.csv     # Sprint 8: per-run baseline ART results
│   ├── baseline_report.md       # Sprint 8: auto-generated analysis report
│   └── random_fleet_log.json    # Sprint 8: placement log for reproducibility
├── src/
│   ├── main.py                  # Entry point for the simulation
│   ├── config.py                # Hyperparameters, paths, and visual constants
│   ├── sim_config_loader.py     # YAML configuration parser
│   ├── run_baseline.py          # Sprint 8: headless batch baseline runner
│   ├── analyze_baseline.py      # Sprint 8: analysis & report generator
│   ├── astar.py                 # Core A* navigation algorithm
│   ├── distance_matrix.py       # Distance matrix computation script
│   ├── intelligence/
│   │   ├── hdbscan.py           # Custom HDBSCAN implementation
│   │   └── demand_clustering.py # Hotspot detection logic
│   ├── rendering/
│   │   ├── pygame_renderer.py   # Pygame visualization logic
│   │   └── visualizer.py        # Matplotlib visualizer + Sprint 8 baseline plots
│   └── simulation/
│       ├── ambulance.py         # Ambulance class & state management
│       ├── assignment.py        # O(1) assignment and tie-breaking logic
│       ├── dispatcher.py        # Centralized dispatcher orchestrator
│       ├── event_spawner.py     # Poisson emergency generation
│       ├── metrics_tracker.py   # Data tracking & CSV export
│       ├── random_fleet.py      # Sprint 8: random station placement generator
│       ├── sim_logger.py        # Multi-level logging configuration
│       ├── simulation_engine.py # Main tick loop
│       └── traffic.py           # Dynamic traffic congestion model
├── tests/                       # Comprehensive Pytest test suite
├── sim_config.yaml              # Centralized simulation parameter configuration
└── headless_baseline.yaml       # Sprint 8: reproducible headless batch config
```

## How to Run

Ensure you have a virtual environment set up with `pygame`, `networkx`, `numpy`, `pyyaml`, and `pytest` installed.

**Run the simulation:**
```bash
python src/main.py
```
- Press **Spacebar** to pause/resume.
- Press **M** to toggle the detailed metrics panel.
- Press **H** to toggle the hotspot overlay.
- Press **T** to toggle the traffic congestion overlay.
- Press **L** to toggle the full log history overlay.

**Run headless (no window):**
```bash
python src/main.py --headless
```

**Run with specific profile:**
You can modify `sim_config.yaml` to change parameters or run headless.

**Run the test suite:**
```bash
pytest tests/ -v
```

---

## Reproducing the Baseline (Sprint 8)

1. Install dependencies into your virtual environment:
```bash
pip install -r requirements.txt
```

2. Run the baseline batch experiment (headless, 10 runs x 1000 ticks):
```bash
python src/run_baseline.py --headless --config headless_baseline.yaml
```

3. Analyze results and generate the report + figures:
```bash
python src/analyze_baseline.py
```

4. View the report:
```
outputs/baseline_report.md
```

Seeds are defined in `headless_baseline.yaml`:
- `random_seed` — controls random fleet station placement
- `event_seed` — controls Poisson event spawning
- `ambulance_seed` — reserved for future randomized ambulance init

Changing any seed will change results. The `random_fleet_log.json` file
records every placement set for full reproducibility auditing.

---

## AI Context Notes
If you are an AI reading this to write future code for this project:
- **Rendering:** `pygame_renderer.py` relies strictly on data passed to its `draw()` method. Do not put simulation state mutations inside the renderer.
- **Distance Matrix:** Never bypass `assignment.py` for calculating proximity. Always use the distance matrix for O(1) lookups to keep the simulation performant, falling back to Euclidean distance only if explicitly necessary.
- **Dependencies:** The graph is loaded as `nx.MultiGraph(G)` (undirected) to prevent ambulances from getting stuck in directed dead-ends.
- **HDBSCAN:** The custom implementation in `src/intelligence/hdbscan.py` is fully tested and robust. It uses an Excess of Mass formula `(birth_level - death_level) * size` for cluster stability extraction.
- **Seeds:** All randomness must flow through `sim_config_loader.py`. Zero hardcoded seeds. Use `event_seed`, `random_seed`, and `ambulance_seed` from config.
- **Headless mode:** Set `SDL_VIDEODRIVER=dummy` BEFORE any `pygame` import. This is enforced in `main.py` and `run_baseline.py`.
