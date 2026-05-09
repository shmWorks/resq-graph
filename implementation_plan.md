# Sprint 10 Implementation Plan: Sensitivity Analysis & Parameter Tuning

**Sprint Goal:** Characterize system performance across key parameter dimensions — event arrival rate, fleet size, and HDBSCAN clustering configuration — using headless batch sweeps, offline Matplotlib analysis, and live Pygame interactive controls.  
**Duration:** Week 10  
**Total Story Points:** 15  
**Visualization Stack:** Pygame (live parameter controls) + Matplotlib (offline sweep plots, saved as PNG)

---

## Table of Contents

1. [Sprint Overview](#sprint-overview)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Dependencies](#prerequisites--dependencies)
4. [US-037 – Sensitivity Analysis on Event Rate (Lambda)](#us-037--sensitivity-analysis-on-event-rate-lambda)
5. [US-038 – Sensitivity Analysis on Number of Ambulances](#us-038--sensitivity-analysis-on-number-of-ambulances)
6. [US-039 – HDBSCAN Sensitivity Analysis](#us-039--hdbscan-sensitivity-analysis)
7. [US-040 – Sensitivity Analysis Report](#us-040--sensitivity-analysis-report)
8. [Live Pygame Controls](#live-pygame-controls)
9. [Integration & Cross-Cutting Concerns](#integration--cross-cutting-concerns)
10. [Testing Strategy](#testing-strategy)
11. [Definition of Done](#definition-of-done)
12. [Risk Register](#risk-register)
13. [Suggested File Structure](#suggested-file-structure)

---

## Sprint Overview

| User Story | Title | Points | Priority |
|---|---|---|---|
| US-037 | Sensitivity Analysis on Event Rate (Lambda) | 4 | High |
| US-038 | Sensitivity Analysis on Number of Ambulances | 4 | High |
| US-039 | HDBSCAN Sensitivity Analysis | 4 | High |
| US-040 | Generate Sensitivity Analysis Report | 3 | Medium |
| **Total** | | **15** | |

> **Algorithm Note:** US-039 tests HDBSCAN parameters (`min_cluster_size`, `min_samples`), not K-Means (`k`). This is a direct consequence of the algorithm decision recorded in the Sprints 6–7 plan. The original PDF's `k=2,3,4` sensitivity analysis is replaced entirely.

---

## Architecture Overview

Each user story follows the same three-layer pattern established in Sprints 8–9:

```
headless_sensitivity.yaml
        │
        ▼
ParameterSweepRunner          (src/run_sensitivity.py)
        │
        ├── SweepConfig  ─────►  SimulationEngine × N runs (headless)
        │                              │
        │                        MetricsTracker
        │                              │
        ▼                              ▼
outputs/sensitivity/           sweep result dicts
  lambda_sweep.csv
  fleet_sweep.csv
  hdbscan_sweep.csv
        │
        ▼
SensitivityAnalyser            (src/analyze_sensitivity.py)
        │
        ├── outputs/figures/   ─── 3 sweep plots (PNG)
        └── outputs/sensitivity_report.md
```

Live Pygame controls are wired into `src/main.py`'s event loop — they are interactive observation tools, not part of the batch sweep pipeline.

---

## Prerequisites & Dependencies

### From Sprints 1–9 (must be complete)

| Dependency | Required For |
|---|---|
| `src/simulation/simulation_engine.py` — headless, seeded | All sweeps |
| `src/simulation/random_fleet.py` — `generate_random_fleet()` | US-037, US-038 baseline runs |
| `outputs/optimal_stations.json` — fixed AI fleet | US-037, US-038 AI runs |
| `src/intelligence/hdbscan.py` — custom HDBSCAN | US-039 |
| `src/intelligence/demand_clustering.py` — `DemandClusterer` | US-039 |
| `src/sim_config_loader.py` — seed management, headless flag | All sweeps |
| `src/rendering/visualizer.py` — matplotlib plotting functions | US-040 |
| `outputs/baseline_results.csv` — Sprint 8 reference ART | US-037, US-038 context |
| `outputs/ai_results.csv` — Sprint 9 reference ART (confirm exists before running) | US-037, US-038 context |

### New Dependencies

No new packages required. `scipy`, `pandas`, `numpy`, `matplotlib` all present from prior sprints.

### New Configuration File (`headless_sensitivity.yaml`)

```yaml
# headless_sensitivity.yaml
# Runs all three parameter sweeps in sequence.
# Run with: python src/run_sensitivity.py --headless --config headless_sensitivity.yaml

meta:
  config_version: "1.0"
  sprint: 10
  description: "Sensitivity analysis sweeps — lambda, fleet size, HDBSCAN"

simulation:
  ticks: 1000
  service_ticks: 10
  num_runs_per_config: 5    # runs averaged per parameter value (speed vs precision tradeoff)

seeds:
  event_seed: 42            # base; offset by run_id per run
  ambulance_seed: 0
  random_seed: 99           # for baseline random fleet generation in sweeps

sweeps:
  lambda:
    values: [0.01, 0.05, 0.1, 0.15]
    fixed_num_ambulances: 5

  fleet_size:
    values: [3, 5, 7, 10]
    fixed_lambda: 0.05

  hdbscan:
    min_cluster_size_values: [3, 5, 8]
    min_samples_values: [2, 3, 5]
    update_interval_values: [25, 50, 100]
    fixed_lambda: 0.05
    fixed_num_ambulances: 5

rendering:
  headless: true
  target_fps: 0
  screen_w: 1200
  screen_h: 900

output:
  figures_dir:        "outputs/figures/"
  sensitivity_dir:    "outputs/sensitivity/"
  report_md:          "outputs/sensitivity_report.md"
```

---

## US-037 – Sensitivity Analysis on Event Rate (Lambda)

**Story Points:** 4  
**Goal:** Characterize how increasing accident arrival rate affects ART for both the random baseline and AI-optimized fleet.

### Sweep Design

```
Lambda values: [0.01, 0.05, 0.1, 0.15]
Fleet types:   [baseline (random), AI (optimal)]
Runs per cell: 5 (averaged)
Total runs:    4 × 2 × 5 = 40 headless simulations
Fixed params:  num_ambulances=5, ticks=1000
```

Each of the 40 runs uses a distinct event seed derived as:
```
event_seed = base_event_seed + (lambda_idx * 100) + run_id
```
This ensures no seed collision between lambda cells while remaining deterministic.

### LambdaSweepRunner

```python
# src/run_sensitivity.py  (LambdaSweepRunner section)

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
                    "std_art":      float(np.std(run_arts, ddof=1)),
                    "mean_events":  float(np.mean(run_events)),
                    "num_runs":     num_runs
                })
                print(f"  λ={lam} | {fleet_type:8s} | ART={np.mean(run_arts):.2f} ± "
                      f"{np.std(run_arts, ddof=1):.2f}")

    def _get_fleet(self, fleet_type: str, num_ambulances: int,
                   run_id: int) -> list[int]:
        """Return fixed AI fleet or a freshly seeded random fleet."""
        if fleet_type == "ai":
            return self.optimal_fleet
        seed = self.config["seeds"]["random_seed"] + run_id
        return generate_random_fleet(self.graph, num_ambulances, seed=seed)

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

    def export_csv(self, path: str = "outputs/sensitivity/lambda_sweep.csv") -> None:
        """Write results to CSV."""
```

### Output: `lambda_sweep.csv`

```
lambda, fleet_type, mean_art, std_art, mean_events, num_runs
0.01, baseline, 4.21, 0.88, 9.8, 5
0.01, ai, 3.05, 0.62, 9.8, 5
0.05, baseline, 8.34, 1.42, 47.3, 5
...
```

### Plot: ART vs Lambda

```
Type:   Dual line plot with error bands
X axis: Lambda (0.01 → 0.15)
Y axis: Mean ART (ticks)
Series: Baseline (red) vs AI (blue)
Extras: ±1 std dev shaded band per series
        Reference points at λ=0.05: Baseline ~25.7 ticks, AI ~23.1 ticks
        (actual Sprint 9 results — annotated as dotted horizontal markers)
        Annotations: "System saturation zone" when ART inflects steeply
Output: outputs/figures/sensitivity_lambda.png
```

### Live Pygame Control: `+` / `-` Keys

Wired into `src/main.py`'s event loop (windowed mode only — not active during headless sweeps):

```python
# src/main.py event loop addition
elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
    config["lambda"] = min(config["lambda"] + 0.01, 0.30)
    engine.event_spawner.set_lambda(config["lambda"])
    logger.info(f"Lambda adjusted to {config['lambda']:.2f}")

elif event.key == pygame.K_MINUS:
    config["lambda"] = max(config["lambda"] - 0.01, 0.001)
    engine.event_spawner.set_lambda(config["lambda"])
    logger.info(f"Lambda adjusted to {config['lambda']:.2f}")
```

The HUD displays the current lambda value so changes are immediately visible. `set_lambda()` is the existing method on `EventSpawner` from Sprint 7.

### Tasks Breakdown

1. Implement `LambdaSweepRunner` in `src/run_sensitivity.py`.
2. Implement `export_csv()` for lambda sweep results.
3. Add `+`/`-` key handlers to `src/main.py` event loop.
4. Update HUD in `src/rendering/pygame_renderer.py` to display current lambda.
5. Implement lambda sweep plot in `src/rendering/visualizer.py`.
6. Verify 40 headless runs complete without error.

---

## US-038 – Sensitivity Analysis on Number of Ambulances

**Story Points:** 4  
**Goal:** Characterize how fleet size affects ART and coverage, and identify diminishing returns.

### Sweep Design

```
Fleet sizes:   [3, 5, 7, 10]
Fleet types:   [baseline (random), AI (optimal)]
Runs per cell: 5 (averaged)
Total runs:    4 × 2 × 5 = 40 headless simulations
Fixed params:  lambda=0.05, ticks=1000
```

Seed derivation:
```
event_seed = base_event_seed + (fleet_size_idx * 100) + run_id
```

**Important note for AI fleet:** The GA was optimized for 5 ambulances. For fleet sizes other than 5, the AI fleet is handled as follows:
- **Fewer than 5 (e.g., 3):** Use the top-3 stations by coverage from `outputs/optimal_stations.json` (ranked by their individual coverage contribution to the fitness function).
- **More than 5 (e.g., 7, 10):** Use all 5 optimal stations plus randomly sampled additional nodes (seeded). Document this as a limitation — the GA was not re-run for these sizes.

### FleetSizeSweepRunner

```python
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

        for size_idx, num_amb in enumerate(fleet_sizes):
            for fleet_type in ["baseline", "ai"]:
                run_arts = []
                for run_id in range(num_runs):
                    fleet = self._get_fleet(fleet_type, num_amb, run_id)
                    seed  = (self.config["seeds"]["event_seed"]
                             + (size_idx * 100) + run_id)
                    art, _ = self._single_run(fleet, lambda_rate, num_amb, seed)
                    run_arts.append(art)

                self.results.append({
                    "num_ambulances": num_amb,
                    "fleet_type":     fleet_type,
                    "mean_art":       float(np.mean(run_arts)),
                    "std_art":        float(np.std(run_arts, ddof=1)),
                    "num_runs":       num_runs
                })

    def _get_fleet(self, fleet_type: str, num_ambulances: int,
                   run_id: int) -> list[int]:
        if fleet_type == "baseline":
            seed = self.config["seeds"]["random_seed"] + run_id
            return generate_random_fleet(self.graph, num_ambulances, seed=seed)
        # AI fleet: scale optimal fleet to requested size
        if num_ambulances <= len(self.optimal_fleet):
            return self.optimal_fleet[:num_ambulances]  # top-N stations
        else:
            extra_seed = self.config["seeds"]["random_seed"] + 1000 + run_id
            extra = generate_random_fleet(
                self.graph,
                num_ambulances - len(self.optimal_fleet),
                seed=extra_seed
            )
            return self.optimal_fleet + extra

    def export_csv(self, path: str = "outputs/sensitivity/fleet_sweep.csv") -> None:
        """Write results to CSV."""
```

### Output: `fleet_sweep.csv`

```
num_ambulances, fleet_type, mean_art, std_art, num_runs
3, baseline, 14.22, 2.31, 5
3, ai, 10.87, 1.95, 5
5, baseline, 8.34, 1.42, 5
5, ai, 5.21, 1.10, 5
...
```

### Plot: ART vs Fleet Size

```
Type:   Dual line plot
X axis: Number of ambulances (3, 5, 7, 10)
Y axis: Mean ART (ticks)
Series: Baseline (red circles) vs AI (blue squares)
Extras: Error bars ±1 std dev
        Annotation: "Diminishing returns" zone where slope flattens
        Reference point at N=5: Baseline ~25.7, AI ~23.1 ticks
        (actual Sprint 9 results — highlighted with a distinct marker)
Output: outputs/figures/sensitivity_fleet_size.png
```

### Live Pygame Control: `A` Key

```python
# src/main.py event loop addition
elif event.key == pygame.K_a:
    new_node = _spawn_new_ambulance(graph, node_positions, distance_matrix, config)
    if new_node is not None:
        engine.add_ambulance(new_node)
        logger.info(f"Ambulance added at node {new_node}. "
                    f"Total: {len(engine.ambulances)}")
```

`engine.add_ambulance(node)` is a new method on `SimulationEngine`:

```python
def add_ambulance(self, start_node: int) -> None:
    """Dynamically add one IDLE ambulance at runtime."""
    new_id = max(a.id for a in self.ambulances) + 1
    amb = Ambulance(id=new_id, start_node=start_node, graph=self.graph)
    self.ambulances.append(amb)
    self.dispatcher.ambulances.append(amb)
```

The HUD updates ambulance count live. This method is the only modification to `SimulationEngine` in this sprint.

### Tasks Breakdown

1. Implement `FleetSizeSweepRunner` in `src/run_sensitivity.py`.
2. Implement AI fleet scaling logic (`_get_fleet()`) with documented limitation.
3. Implement `export_csv()` for fleet sweep results.
4. Implement `engine.add_ambulance()` method on `SimulationEngine`.
5. Add `A` key handler to `src/main.py` event loop.
6. Implement fleet size sweep plot in `src/rendering/visualizer.py`.
7. Verify 40 headless runs complete without error.

---

## US-039 – HDBSCAN Sensitivity Analysis

**Story Points:** 4  
**Goal:** Identify optimal HDBSCAN `min_cluster_size`, `min_samples`, and `rebalance_interval` settings that minimize ART without causing excessive ambulance churn.

> **Replaces:** The original PDF's K-Means `k` sensitivity analysis. Per the algorithm decision documented in the Sprints 6–7 plan, HDBSCAN replaced K-Means and has no `k` parameter. This story tests `min_cluster_size` and `min_samples` instead.

### Parameters Under Test

| Parameter | Values Tested | What It Controls |
|---|---|---|
| `min_cluster_size` | 3, 5, 8 | Minimum accidents to form a hotspot; higher = fewer, more stable clusters |
| `min_samples` | 2, 3, 5 | Core point density threshold; higher = more conservative clustering |
| `rebalance_interval` | 25, 50, 100 | Ticks between HDBSCAN runs; lower = more reactive, higher churn |

### Sweep Design

Full factorial over all three parameters:

```
min_cluster_size:   [3, 5, 8]      → 3 values
min_samples:        [2, 3, 5]      → 3 values
rebalance_interval: [25, 50, 100]  → 3 values
Runs per cell:      3 (averaged — reduced from 5 due to 27-cell grid)
Total runs:         3 × 3 × 3 × 3 = 81 headless simulations
Fixed params:       AI fleet, lambda=0.05, num_ambulances=5, ticks=1000
```

Only the AI fleet is tested — HDBSCAN rebalancing is only meaningful when dispatch quality is controlled.

### Metrics Collected Per Cell

| Metric | Description |
|---|---|
| `mean_art` | Primary performance metric |
| `std_art` | Variance across runs |
| `mean_rebalance_count` | Average times rebalancing fired per run |
| `mean_clusters_detected` | Average hotspots found per HDBSCAN call |
| `mean_noise_fraction` | Fraction of accidents classified as noise |

### HDBSCANSweepRunner

```python
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

        for mcs in sweep_cfg["min_cluster_size_values"]:
            for ms in sweep_cfg["min_samples_values"]:
                for interval in sweep_cfg["update_interval_values"]:
                    run_arts, run_rebalances, run_clusters, run_noise = [], [], [], []

                    for run_id in range(num_runs):
                        seed = (self.config["seeds"]["event_seed"]
                                + (cell_idx * 100) + run_id)
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
                        "std_art":                float(np.std(run_arts, ddof=1)),
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
        """
        Runs the engine with patched HDBSCAN params.
        DemandClusterer and DispatcherBrain receive updated params at init.
        """
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
        engine.run()
        t = engine.metrics_tracker
        d = engine.dispatcher
        return {
            "art":              t.art,
            "rebalance_count":  d.rebalance_count,
            "mean_clusters":    d.mean_clusters_per_rebalance,
            "noise_fraction":   d.mean_noise_fraction
        }

    def export_csv(self, path: str = "outputs/sensitivity/hdbscan_sweep.csv") -> None:
        """Write full factorial results to CSV."""
```

### Required Engine Interface Additions

`SimulationEngine` must accept `hdbscan_min_cluster_size`, `hdbscan_min_samples`, and `rebalance_interval` as constructor parameters and pass them through to `DemandClusterer` and `DispatcherBrain`. These are the only additions to the engine for this sprint.

`DispatcherBrain` must expose:
- `rebalance_count: int` — incremented each time `rebalance_fleet()` is called
- `mean_clusters_per_rebalance: float` — rolling mean of clusters found
- `mean_noise_fraction: float` — rolling mean of noise fraction

These counters are already consistent with the logging system from Sprint 7; they just need to be surfaced as public attributes.

### Output: `hdbscan_sweep.csv`

```
min_cluster_size, min_samples, rebalance_interval, mean_art, std_art, mean_rebalance_count, mean_clusters_detected, mean_noise_fraction
3, 2, 25, 5.44, 1.21, 38.2, 2.1, 0.18
3, 2, 50, 5.61, 1.18, 19.4, 2.0, 0.19
...
```

### Plots: HDBSCAN Sensitivity

Two plots are generated:

**Plot A — ART Heatmap (min_cluster_size × min_samples, one panel per interval):**
```
Type:   3-panel heatmap grid (one per rebalance_interval)
X axis: min_samples (2, 3, 5)
Y axis: min_cluster_size (3, 5, 8)
Colour: mean_art (green=low, red=high)
Output: outputs/figures/sensitivity_hdbscan_art.png
```

**Plot B — Rebalance Churn vs ART (scatter):**
```
Type:   Scatter plot
X axis: mean_rebalance_count (proxy for churn)
Y axis: mean_art
Colour: rebalance_interval (3 distinct colours)
Marker: shape = min_cluster_size group
Extras: Pareto frontier line (lowest ART for given churn level)
        Annotation: recommended operating point
Output: outputs/figures/sensitivity_hdbscan_churn.png
```

### Recommendation Logic

After the sweep, the analyser selects the recommended configuration:

```python
def recommend_hdbscan_config(df: pd.DataFrame) -> dict:
    """
    Select configuration minimizing ART subject to:
      - mean_rebalance_count <= median rebalance_count
        (avoid excessive churn)
      - mean_noise_fraction <= 0.3
        (clustering must be meaningful, not all noise)
    """
    filtered = df[
        (df["mean_rebalance_count"] <= df["mean_rebalance_count"].median()) &
        (df["mean_noise_fraction"] <= 0.30)
    ]
    if filtered.empty:
        # Fallback: pure ART minimizer
        return df.loc[df["mean_art"].idxmin()].to_dict()
    return filtered.loc[filtered["mean_art"].idxmin()].to_dict()
```

### Live Pygame Control: `K` Key

```python
# src/main.py event loop addition
elif event.key == pygame.K_k:
    clusters = engine.dispatcher.demand_clusterer.run(
        engine.dispatcher.active_events
    )
    engine.dispatcher._rebalance_to_clusters(clusters, engine.current_tick)
    logger.info(f"Manual HDBSCAN triggered: {len(clusters)} clusters found")
```

The HUD briefly flashes "HDBSCAN triggered" for 60 ticks after the key press to confirm activation.

### Tasks Breakdown

1. Implement `HDBSCANSweepRunner` in `src/run_sensitivity.py`.
2. Add `hdbscan_min_cluster_size`, `hdbscan_min_samples`, `rebalance_interval` params to `SimulationEngine.__init__()`.
3. Surface `rebalance_count`, `mean_clusters_per_rebalance`, `mean_noise_fraction` on `DispatcherBrain`.
4. Implement `export_csv()` for HDBSCAN sweep.
5. Implement `recommend_hdbscan_config()` in `src/analyze_sensitivity.py`.
6. Implement both heatmap and scatter plots in `src/rendering/visualizer.py`.
7. Add `K` key handler to `src/main.py` event loop.
8. Verify 81 headless runs complete without error or HDBSCAN exception.

---

## US-040 – Sensitivity Analysis Report

**Story Points:** 3  
**Goal:** Auto-generate a comprehensive Markdown report compiling all three sensitivity analyses.

### Report Structure

```markdown
# ResQ-Graph: Sensitivity Analysis Report

**Generated:** {timestamp}
**Config Version:** 1.0
**Sprint:** 10

---

## Executive Summary

| Analysis | Key Finding | Recommended Value |
|---|---|---|
| Event Rate (λ) | AI fleet maintains advantage across all λ | λ = 0.05 (baseline config) |
| Fleet Size (N) | Diminishing returns beyond N=7 | N = 5 (cost-performance optimum) |
| HDBSCAN Config | {best config from recommend_hdbscan_config()} | mcs=X, ms=Y, interval=Z |

---

## 1. Event Rate (Lambda) Sensitivity

### Methodology
- Lambda values tested: 0.01, 0.05, 0.1, 0.15
- Runs per value: 5 (each fleet type)
- Fixed: 5 ambulances, 1000 ticks

### Results Table
| Lambda | Baseline ART | AI ART | Improvement |
|---|---|---|---|
| 0.01 | X.XX | X.XX | XX% |
...

### Visualization
![Lambda Sensitivity](figures/sensitivity_lambda.png)

### Analysis
{Auto-generated: at which lambda does the AI advantage erode?
 At which lambda does the system saturate (ART grows non-linearly)?}

---

## 2. Fleet Size Sensitivity

### Methodology
- Fleet sizes tested: 3, 5, 7, 10
- Limitation: AI fleet for N≠5 uses scaled/padded optimal stations
  (GA was optimized only for N=5)

### Results Table
| Fleet Size | Baseline ART | AI ART | Improvement |
|---|---|---|---|
| 3 | X.XX | X.XX | XX% |
...

### Visualization
![Fleet Size Sensitivity](figures/sensitivity_fleet_size.png)

### Analysis
{Auto-generated: slope analysis to identify diminishing returns threshold}

---

## 3. HDBSCAN Parameter Sensitivity

### Methodology
- Parameters: min_cluster_size ∈ {3,5,8}, min_samples ∈ {2,3,5},
  rebalance_interval ∈ {25,50,100}
- Runs per cell: 3
- Fixed: AI fleet, λ=0.05, 5 ambulances, 1000 ticks

### Recommended Configuration
| Parameter | Value | Rationale |
|---|---|---|
| min_cluster_size | X | {rationale} |
| min_samples | X | {rationale} |
| rebalance_interval | X | {rationale} |

### Visualizations
![HDBSCAN ART Heatmap](figures/sensitivity_hdbscan_art.png)
![HDBSCAN Churn vs ART](figures/sensitivity_hdbscan_churn.png)

### Trade-offs: Responsiveness vs Churn
{Auto-generated discussion: lower interval = faster response to hotspots,
 but more ambulance movement = fewer available for immediate dispatch.}

---

## 4. Recommended Configuration

Based on all analyses, the recommended production configuration is:

```yaml
lambda: 0.05
num_ambulances: 5
hdbscan:
  min_cluster_size: X
  min_samples: X
  rebalance_interval: X
```

## 5. Future Optimization Directions

- Re-run GA for fleet sizes N=3, 7, 10 to get true optimal baselines.
- Test HDBSCAN with `min_cluster_size` tied to fleet size (e.g., mcs = N).
- Explore non-uniform lambda (time-of-day demand variation).
- Investigate RL-based dispatcher as alternative to rule-based assignment.
```

### SensitivityAnalyser

```python
# src/analyze_sensitivity.py

class SensitivityAnalyser:
    def __init__(self, lambda_csv: str, fleet_csv: str, hdbscan_csv: str):
        self.lambda_df  = pd.read_csv(lambda_csv)
        self.fleet_df   = pd.read_csv(fleet_csv)
        self.hdbscan_df = pd.read_csv(hdbscan_csv)

    def generate_all_plots(self, figures_dir: str) -> None:
        """Calls visualizer.py for all 4 sensitivity plots."""

    def recommend_hdbscan_config(self) -> dict:
        """Returns best HDBSCAN config dict per recommendation logic."""

    def generate_report(self, output_path: str) -> None:
        """Auto-generates sensitivity_report.md."""
```

### Tasks Breakdown

1. Implement `SensitivityAnalyser` in `src/analyze_sensitivity.py`.
2. Implement `generate_report()` with all five sections.
3. Add all sensitivity plot functions to `src/rendering/visualizer.py`.
4. Write `src/analyze_sensitivity.py` as both module and entry point.
5. Verify report renders correctly in GitHub Markdown preview.
6. Verify recommended config is written back to a `recommended_config.yaml` for downstream use.

---

## Live Pygame Controls

This section consolidates all three new key bindings added to `src/main.py`:

| Key | Action | Component Modified |
|---|---|---|
| `+` / `=` | Increase lambda by 0.01 (max 0.30) | `EventSpawner.set_lambda()` |
| `-` | Decrease lambda by 0.01 (min 0.001) | `EventSpawner.set_lambda()` |
| `A` | Add one IDLE ambulance at a random node | `SimulationEngine.add_ambulance()` |
| `K` | Manually trigger HDBSCAN rebalance now | `DispatcherBrain` direct call |

### HUD Updates

The existing HUD panel gains two new lines to surface live parameter state:

```
┌─────────────────────────────────────┐
│  Tick:               1042           │
│  Active Events:      3              │
│  Idle Ambulances:    2 / 6          │  ← N updates when A pressed
│  Avg Response Time:  6.4 ticks      │
│  Events Resolved:    47             │
│  Fleet Utilisation:  67%            │
│  Lambda (λ):         0.07           │  ← NEW: updates on +/-
│  Last HDBSCAN:       tick 1000      │  ← NEW: updates on K or auto
└─────────────────────────────────────┘
```

### Design Constraints for Live Controls

- Live controls affect the **running simulation** only — they do not modify `sim_config.yaml` or `headless_sensitivity.yaml`.
- Lambda changes are not retroactive — events already spawned at a higher rate remain active.
- Adding ambulances with `A` uses the same `generate_random_fleet()` logic with a time-based seed to avoid determinism issues in the live window.
- `K` key triggers a single rebalance call immediately, independent of the `rebalance_interval` timer.
- All three controls log their actions via `sim_logger.py` at INFO level.

---

## Integration & Cross-Cutting Concerns

### Sweep Runner Entry Point

All three sweep runners are orchestrated from a single entry point:

```bash
python src/run_sensitivity.py --headless --config headless_sensitivity.yaml
```

The runner executes sweeps in order (lambda → fleet → HDBSCAN) and logs progress:
```
[Sensitivity] Starting lambda sweep (40 runs)...
[Sensitivity] Lambda sweep complete. CSV saved.
[Sensitivity] Starting fleet size sweep (40 runs)...
[Sensitivity] Fleet sweep complete. CSV saved.
[Sensitivity] Starting HDBSCAN sweep (81 runs)...
[Sensitivity] HDBSCAN sweep complete. CSV saved.
[Sensitivity] Total wall time: XX.X minutes
```

**Headless enforcement:** Per the README AI context note, `SDL_VIDEODRIVER=dummy` must be set **before** any `pygame` import. `run_sensitivity.py` must follow the same pattern as `run_baseline.py` — read the config, set the env var, then import/init pygame. Never set it after `pygame.init()`.

The analysis and report are generated separately:
```bash
python src/analyze_sensitivity.py
```

### What This Sprint Does NOT Modify

- `src/rendering/pygame_renderer.py` — HUD text additions only (no structural change)
- `src/simulation/dispatcher.py` — only new public counter attributes added
- `src/simulation/ambulance.py` — unchanged
- `src/intelligence/hdbscan.py` — unchanged (params passed in, algorithm unchanged)
- `sim_config.yaml` — unchanged (sweep uses `headless_sensitivity.yaml`)

### Seed Isolation Across Sweeps

Each sweep uses a different seed offset range to prevent cross-contamination:
```
lambda sweep:     event_seed + (lambda_idx   * 100) + run_id
fleet sweep:      event_seed + (fleet_idx    * 100) + run_id  (+ 1000 base offset)
HDBSCAN sweep:    event_seed + (cell_idx     * 100) + run_id  (+ 5000 base offset)
```

The base offsets (0, 1000, 5000) are constants in `run_sensitivity.py`, not in the config.

### AI Fleet Scaling Limitation (US-038)

The plan to use `optimal_fleet[:N]` for N<5 and `optimal_fleet + random_extra` for N>5 is a known limitation — the GA was optimized only for N=5. This limitation is:
1. Documented in the `_get_fleet()` docstring.
2. Noted explicitly in the US-040 report methodology section.
3. Listed under "Future Optimization Directions" in the report.

---

## Testing Strategy

### US-037 — Lambda Sweep Tests

| Test | Assertion |
|---|---|
| Seed isolation | Runs at λ=0.01 and λ=0.15 use different event seeds |
| ART increases with λ | `mean_art` monotonically increases across λ values (approximate) |
| CSV schema | `lambda_sweep.csv` has all required columns |
| `+` key | `engine.event_spawner.lambda_rate` increases after keypress |
| `-` key | Lambda does not go below 0.001 |

### US-038 — Fleet Sweep Tests

| Test | Assertion |
|---|---|
| Fleet scaling — fewer | `len(ai_fleet) == 3` when `num_ambulances=3` |
| Fleet scaling — more | `len(ai_fleet) == 7` when `num_ambulances=7`; extra nodes not in optimal_fleet |
| ART decreases with fleet size | `mean_art` generally decreases as N increases |
| `add_ambulance()` | `len(engine.ambulances)` increments by 1 after call |
| `A` key | New ambulance appears in IDLE state in renderer |

### US-039 — HDBSCAN Sweep Tests

| Test | Assertion |
|---|---|
| Cell count | `len(results) == 27` after full sweep (3×3×3) |
| No HDBSCAN crash | Engine runs 3 runs per cell at all 27 parameter combos without error |
| Noise fraction bounds | `0.0 <= mean_noise_fraction <= 1.0` for all rows |
| Recommendation filter | `recommend_hdbscan_config()` returns a single config dict |
| `K` key | `dispatcher.rebalance_count` increments by 1 after keypress |
| Low `min_cluster_size` | mcs=3 produces more clusters and lower noise fraction than mcs=8 |

### US-040 — Report Tests

| Test | Assertion |
|---|---|
| All 4 PNGs created | Files exist in `outputs/figures/` after `generate_all_plots()` |
| Report created | `outputs/sensitivity_report.md` exists and is non-empty |
| Recommended config | `recommended_config.yaml` written with all three HDBSCAN params |
| Section count | Report contains all 5 sections |

---

## Definition of Done

- All acceptance criteria from both the original and Pygame-updated specification are met.
- HDBSCAN sensitivity replaces K-Means sensitivity throughout (no reference to `k` parameter).
- 40 lambda sweep runs + 40 fleet sweep runs + 81 HDBSCAN sweep runs complete headless without error.
- All 4 Matplotlib plots saved to `outputs/figures/` as PNG.
- `lambda_sweep.csv`, `fleet_sweep.csv`, `hdbscan_sweep.csv` present in `outputs/sensitivity/`.
- `+`/`-`, `A`, and `K` key controls functional in windowed mode; HUD displays updated values.
- `sensitivity_report.md` auto-generated with all five sections populated.
- `recommended_config.yaml` written with final HDBSCAN recommendation.
- Unit tests pass for all new sweep runners and live controls.
- Sprint board card moved to Done.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 81 HDBSCAN runs too slow (> 20 min) | Medium | Medium | Reduce `num_runs_per_config` to 3; note in report |
| HDBSCAN raises exception at extreme params (mcs=8, ms=5 with few events) | Medium | High | Wrap `_single_run()` in try/except; log failed cells; skip in analysis |
| AI fleet scaling for N≠5 produces misleading results | Medium | Medium | Document limitation prominently; grey out N≠5 AI data points in plot |
| `A` key adds ambulance without graph/dispatcher sync | Low | High | `add_ambulance()` must update both `engine.ambulances` and `dispatcher.ambulances` atomically |
| Lambda live control interferes with headless sweep | None | High | `+`/`-` handlers guarded by `if not config["headless"]` check |
| Seed collision across sweep types | Low | Medium | Confirmed by base offset constants (0, 1000, 5000) — assert no overlap in tests |

---

## Suggested File Structure

The structure below is grounded in the README file tree (current as of Sprint 9). Files marked "From Sprint 9" exist as Sprint 9 deliverables but are not yet reflected in the README's file tree. All new Sprint 10 files are marked "NEW".

```
resq-graph/
├── data/
│   ├── model_town.graphml             # Unchanged
│   ├── node_positions.json            # Unchanged
│   ├── map_bg.png                     # Unchanged
│   ├── distance_matrix.npy            # Unchanged
│   └── traffic_distance_matrix.npy    # From Sprint 9
├── outputs/
│   ├── figures/                       # ALL matplotlib plots (exists per README)
│   │   ├── [Sprint 8 baseline plots]  # Already present per README
│   │   ├── [Sprint 9 comparison plots] # From Sprint 9 — confirm present
│   │   ├── sensitivity_lambda.png             # NEW
│   │   ├── sensitivity_fleet_size.png         # NEW
│   │   ├── sensitivity_hdbscan_art.png        # NEW
│   │   └── sensitivity_hdbscan_churn.png      # NEW
│   ├── sensitivity/                           # NEW directory
│   │   ├── lambda_sweep.csv                   # NEW
│   │   ├── fleet_sweep.csv                    # NEW
│   │   └── hdbscan_sweep.csv                  # NEW
│   ├── baseline_results.csv           # Sprint 8 — confirmed in README
│   ├── baseline_report.md             # Sprint 8 — confirmed in README
│   ├── random_fleet_log.json          # Sprint 8 — confirmed in README
│   ├── optimal_stations.json          # From Sprint 3
│   ├── ai_results.csv                 # From Sprint 9 — confirm present
│   ├── ai_response_times.csv          # From Sprint 9 — confirm present
│   ├── comparison_metrics.json        # From Sprint 9 — confirm present
│   ├── comparison_report.md           # From Sprint 9 — confirm present
│   ├── sensitivity_report.md          # NEW: auto-generated by analyze_sensitivity.py
│   └── recommended_config.yaml        # NEW: HDBSCAN recommendation output
├── src/
│   ├── main.py                        # UPDATED: +/-, A, K key handlers + 2 new HUD lines
│   ├── config.py                      # Unchanged
│   ├── sim_config_loader.py           # Unchanged
│   ├── run_baseline.py                # Sprint 8 — confirmed in README
│   ├── analyze_baseline.py            # Sprint 8 — confirmed in README
│   ├── run_ai_fleet.py                # From Sprint 9 — confirm present
│   ├── analyze_comparison.py          # From Sprint 9 — confirm present
│   ├── split_screen_demo.py           # From Sprint 9 — confirm present
│   ├── run_sensitivity.py             # NEW: all three sweep runners + entry point
│   ├── analyze_sensitivity.py         # NEW: SensitivityAnalyser + entry point
│   ├── astar.py                       # Unchanged
│   ├── distance_matrix.py             # Unchanged
│   ├── intelligence/
│   │   ├── hdbscan.py                 # Unchanged
│   │   ├── demand_clustering.py       # Unchanged
│   │   └── traffic_profiler.py        # From Sprint 9
│   ├── rendering/
│   │   ├── pygame_renderer.py         # UPDATED: 2 new HUD lines (lambda, last HDBSCAN tick)
│   │   └── visualizer.py             # UPDATED: 4 new sensitivity plot functions
│   └── simulation/
│       ├── ambulance.py               # Unchanged
│       ├── assignment.py              # Unchanged
│       ├── dispatcher.py              # UPDATED: rebalance_count, mean_clusters, mean_noise attrs
│       ├── event_spawner.py           # Unchanged (set_lambda() exists from Sprint 7)
│       ├── metrics_tracker.py         # Unchanged
│       ├── random_fleet.py            # Sprint 8 — confirmed in README
│       ├── sim_logger.py              # Unchanged
│       ├── simulation_engine.py       # UPDATED: add_ambulance(), hdbscan/rebalance params
│       └── traffic.py                 # Unchanged
├── tests/                             # Confirmed in README
│   ├── [existing Sprint 1–9 tests]    # Unchanged
│   ├── test_run_sensitivity.py        # NEW: all three sweep runners
│   └── test_analyze_sensitivity.py    # NEW: analyser + recommendation logic
├── headless_sensitivity.yaml          # NEW: committed to repo root
├── headless_ai.yaml                   # From Sprint 9 — confirm present
├── headless_baseline.yaml             # Sprint 8 — confirmed in README
├── sim_config.yaml                    # Confirmed in README — unchanged
└── README.md                          # UPDATED: Sprint 10 run instructions
```

---

*Plan prepared for Sprint 10 — Week 10. File structure is grounded in the README tree current as of Sprint 9. All new scripts follow the `src/` convention from Sprints 8–9. Plots go to `outputs/figures/`. Raw sweep CSVs go to the new `outputs/sensitivity/` subdirectory. The HDBSCAN sensitivity analysis replaces the original K-Means `k` sensitivity per the algorithm decision in the Sprints 6–7 plan. Actual Sprint 9 ART results: Baseline ~25.7 ticks, AI ~23.1 ticks (+10.3% improvement, p < 0.01) — use these as reference points in sweep plots.*