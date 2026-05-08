# Sprint 8 Implementation Plan
## Baseline Comparison & Random Fleet (Week 8)

**Sprint Goal:** Establish a performance baseline using random station placement and add headless mode for batch experiments.

> **Codebase context:** This sprint extends ResQ-Graph as it stands after Sprint 7. All new code must respect the existing architecture — use `assignment.py` for proximity lookups, never mutate simulation state inside `pygame_renderer.py`, and load the graph as `nx.MultiGraph`. Seeds and parameters must flow through the YAML config system (`sim_config_loader.py`).

---

## Overview

| Story | Title | Points |
|-------|-------|--------|
| US-029 | Random Station Placement Generator | 2 |
| US-030 | Run Simulation with Random Fleet (Baseline) | 5 |
| US-031 | Document Random Fleet Baseline Results | 3 |
| US-032 | Baseline Configuration & Reproducibility Seed | 2 |
| **Total** | | **12** |

---

## US-029 · Random Station Placement Generator
**As a baseline engineer, I want a random fleet so that I have a control group.**

### Acceptance Criteria
- Generate 5 unique random node IDs from the graph (no duplicates)
- Repeat generation N times (default: 10) to support averaged baseline calculation
- All random placements logged for reproducibility
- Function returns a list of node IDs

### Implementation Tasks

#### 1. New file: `src/simulation/random_fleet.py`
- Implement `generate_random_fleet(graph, n_stations, n_repeats, seed)`:
  - Use `random.sample(list(graph.nodes()), n_stations)` inside a seeded RNG — the graph is already loaded as `nx.MultiGraph` in the engine, so accept it as a parameter rather than re-loading it
  - Return a list of lists: `[[node_id, ...], ...]` — one inner list per repeat
- Read `n_stations`, `n_repeats`, and `random_seed` from the config dict passed in, consistent with how other modules consume config values via `sim_config_loader.py`

#### 2. Logging
- Write each generated placement set to `outputs/random_fleet_log.json` (alongside existing CSV outputs in `outputs/`)
- Each entry: `{ "repeat": i, "seed": seed, "nodes": [...], "timestamp": "..." }`
- Use the existing `sim_logger.py` logging infrastructure for console output rather than setting up a separate logger

#### 3. Tests: `tests/test_random_fleet.py`
- Confirm no duplicate node IDs within a single placement set
- Confirm same seed always produces identical output
- Confirm output dimensions match `n_stations` × `n_repeats`
- Run via `pytest tests/ -v` as per project convention

---

## US-030 · Run Simulation with Random Fleet (Baseline)
**As a researcher, I want a baseline ART so that optimization gains are measurable.**

### Acceptance Criteria
- Run simulation **10 times** with different random seeds
- Each run executes **1000+ ticks** with Poisson event spawning
- **Headless mode** via `--headless` flag (`SDL_VIDEODRIVER=dummy` set before `pygame.init()`)
- Collect ART (Average Response Time) per run
- Calculate mean ART and standard deviation across all runs
- Results exported to CSV

### Implementation Tasks

#### 1. Refactor `run_simulation()` in `src/simulation/simulation_engine.py`
Currently, `run_simulation()` parses its own arguments. Refactor it to support programmatic injection:
- Accept `cfg: dict = None` and `initial_nodes: list[int] = None` as optional arguments.
- If `initial_nodes` is provided, use them instead of the default modulo-based node selection.
- This allows `run_baseline.py` to execute the simulation loop without duplicating setup logic.

#### 2. Headless flag in `src/main.py`
`src/main.py` is the project's single entry point. Add headless support there:

```python
import argparse, os

parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true")
parser.add_argument("--config", default="sim_config.yaml")
args = parser.parse_args()

if args.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame  # must come AFTER the env var is set
pygame.init()
```

- `SDL_VIDEODRIVER=dummy` **must** be set before `pygame.init()` — since `pygame_renderer.py` is imported downstream, this ordering is enforced by keeping the flag check at the very top of `main.py` before any other project imports
- When `--headless` is active, the renderer's `draw()` call can be skipped entirely (wrap in `if not args.headless`) — this respects the architecture rule that the renderer must never hold simulation state

#### 2. Baseline runner script: `src/run_baseline.py`
- Accepts `--headless`, `--config`, and optionally `--seeds` (list) and `--ticks`
- Loops over 10 seeds (sourced from `headless_baseline.yaml` via `sim_config_loader.py`):
  - Calls `generate_random_fleet()` with the current seed to get starting node IDs
  - Instantiates `SimulationEngine` with those node IDs and runs for ≥ 1000 ticks
  - Uses the existing `MetricsTracker` (already in `src/simulation/metrics_tracker.py`) to collect per-run ART — do not implement a separate metrics system
- All batch runs must pass `--headless` to avoid requiring a display

#### 3. Results export: `outputs/baseline_results.csv`
- Reuse `MetricsTracker`'s export logic where possible; extend it if needed to accept a `run_id` column
- Final CSV columns:
  ```
  run_id, seed, n_events, mean_art, std_art, ticks
  ```
- Append a summary row (mean and std dev across all 10 runs) at the bottom

---

## US-031 · Document Random Fleet Baseline Results
**As an analyst, I want clear baseline documentation so that comparisons are meaningful.**

### Acceptance Criteria
- Report includes: baseline ART, std dev, number of events processed
- Visualizations generated with **matplotlib** (offline, no display required):
  - ART distribution histogram
  - Time-series of response times per run
- Analysis covers observed inefficiencies of random placement
- Markdown report generated automatically from the analysis script

### Implementation Tasks

#### 1. Analysis script: `src/analyze_baseline.py`
- Reads `outputs/baseline_results.csv`
- Computes summary statistics: mean ART, std dev, min/max ART, total events processed

#### 2. Visualizations using `src/visualizer.py`
The project already has a legacy matplotlib visualizer at `src/visualizer.py`. 
- **Task**: Move `src/visualizer.py` to `src/rendering/visualizer.py` to maintain architectural consistency.
- Add the baseline figures there as new functions:
  - `plot_art_distribution(results_df)` — histogram of ART across all 10 runs
    - Saved to `outputs/figures/art_distribution.png`
  - `plot_art_timeseries(results_df)` — per-run response time series, overlaid
    - Saved to `outputs/figures/art_timeseries.png`
- Call `matplotlib.use("Agg")` at the top of `visualizer.py` (already present) to ensure offline/headless rendering.

#### 3. Auto-generated report: `outputs/baseline_report.md`
`analyze_baseline.py` writes this file programmatically, including:
- Summary statistics table
- Embedded figure references (`![ART Distribution](figures/art_distribution.png)`)
- Written observations on random placement inefficiencies (e.g., spatial clustering, uncovered zones, long travel distances vs. optimized placement)
- Pointers for the optimized fleet comparison in later sprints

---

## US-032 · Baseline Configuration & Reproducibility Seed
**As a researcher, I want reproducible results so that experiments are valid.**

### Acceptance Criteria
- Baseline seed documented (`random_seed` for random fleet generation)
- Simulation seeds set for both event spawning and ambulance initialization
- Config version tracked
- `headless_baseline.yaml` added to repo alongside the windowed config
- README documents how to reproduce the full baseline run

### Implementation Tasks

#### 1. New config file: `headless_baseline.yaml`
Add this at the project root alongside the existing `sim_config.yaml`:

```yaml
config_version: "1.0.0"

# Reproducibility seeds
random_seed: 42        # controls random fleet generation (random_fleet.py)
event_seed: 100        # controls Poisson event spawning (event_spawner.py)
ambulance_seed: 200    # controls ambulance initialization order

# Baseline experiment parameters
n_stations: 5
n_repeats: 10
ticks_per_run: 1000
headless: true
```

- All three seed values must be consumed via `sim_config_loader.py` — no hardcoded seeds anywhere in the codebase
- `sim_config.yaml` (the windowed interactive config) remains **unchanged**

#### 2. Seed propagation
- `event_spawner.py`: pass `event_seed` to its RNG at initialization
- `ambulance.py` initialization: use `ambulance_seed` if any randomness is involved in setup
- `random_fleet.py`: uses `random_seed` as shown in US-029
- `ambulance.py`: currently deterministic, but `ambulance_seed` is provided to the simulation for future-proofing any randomized setup logic.

#### 3. README update
Add a **"Reproducing the Baseline (Sprint 8)"** section to `README.md`:

```markdown
## Reproducing the Baseline (Sprint 8)

1. Install dependencies into your virtual environment:
   pip install -r requirements.txt

2. Run the baseline batch experiment (headless):
   python src/run_baseline.py --headless --config headless_baseline.yaml

3. Analyze results and generate the report:
   python src/analyze_baseline.py

4. View the report:
   outputs/baseline_report.md

Seeds are defined in headless_baseline.yaml. random_seed controls fleet
placement, event_seed controls Poisson spawning, and ambulance_seed controls
ambulance initialization. Changing any seed will change results.
```

---

## Updated File & Directory Structure

Only **new or modified** files are marked; everything else is unchanged from Sprint 7.

```
resq-graph/
├── data/                          (unchanged)
├── outputs/
│   ├── baseline_results.csv       [NEW] US-030: raw per-run results
│   ├── baseline_report.md         [NEW] US-031: auto-generated report
│   ├── random_fleet_log.json      [NEW] US-029: placement logs
│   └── figures/
│       ├── art_distribution.png   [NEW] US-031
│       └── art_timeseries.png     [NEW] US-031
├── src/
│   ├── main.py                    [MODIFIED] US-030: --headless flag added
│   ├── config.py                  (unchanged)
│   ├── sim_config_loader.py       (unchanged)
│   ├── run_baseline.py            [NEW] US-030: batch runner
│   ├── analyze_baseline.py        [NEW] US-031: analysis & report generator
│   ├── intelligence/              (unchanged)
│   ├── rendering/
│   │   ├── pygame_renderer.py     (unchanged — no state mutations)
│   │   └── visualizer.py          [MOVED & MODIFIED] US-031: moved from src/ and new plots added
│   └── simulation/
│       ├── simulation_engine.py   [MODIFIED] US-030: refactored for programmatic injection
│       ├── random_fleet.py        [NEW] US-029: fleet generator
│       ├── event_spawner.py       [MODIFIED] US-032: event_seed wired in
│       ├── ambulance.py           [MODIFIED] US-032: ambulance_seed wired in
│       └── ... (all others unchanged)
├── tests/
│   └── test_random_fleet.py       [NEW] US-029: unit tests
├── sim_config.yaml                (unchanged — windowed config)
├── headless_baseline.yaml         [NEW] US-032: headless/batch config
└── README.md                      [MODIFIED] US-032: reproduction steps added
```

---

## Definition of Done

- [x] `generate_random_fleet()` passes all Pytest tests; no duplicates; same seed → same output
- [x] `--headless` in `main.py` sets `SDL_VIDEODRIVER=dummy` before any `pygame` import
- [x] Renderer `draw()` call is skipped cleanly in headless mode — no state mutations
- [x] `run_baseline.py` completes 10 runs × 1000+ ticks headlessly without errors
- [x] `MetricsTracker` used for ART collection (no parallel metrics system)
- [x] `baseline_results.csv` written to `outputs/` with all 10 runs + summary row
- [x] Both matplotlib figures saved via `Agg` backend to `outputs/figures/`
- [x] `baseline_report.md` auto-generated with stats, embedded figures, and analysis
- [x] `headless_baseline.yaml` committed with all three seeds documented
- [x] `sim_config.yaml` (windowed) remains untouched and fully functional
- [x] All seeds flow through `sim_config_loader.py` — zero hardcoded values
- [x] README updated with reproduction steps referencing correct entry points
- [x] All new tests pass under `pytest tests/ -v`