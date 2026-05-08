# Sprint 9 Implementation Plan: AI-Optimized Fleet & Comparison

**Sprint Goal:** Run the GA-optimized fleet under identical conditions to the Sprint 8 baseline, perform rigorous statistical comparison, produce publication-quality visualizations, and deliver a comprehensive results summary — all culminating in a live Pygame split-screen demo.  
**Duration:** Week 9  
**Total Story Points:** 17  
**Visualization Stack:** Pygame (split-screen demo) + Matplotlib (offline analysis, saved as PNG)

---

## Table of Contents

1. [Sprint Overview](#sprint-overview)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Dependencies](#prerequisites--dependencies)
4. [US-033 – Run Simulation with AI-Optimized Fleet](#us-033--run-simulation-with-ai-optimized-fleet)
5. [US-034 – Head-to-Head Comparison Analysis](#us-034--head-to-head-comparison-analysis)
6. [US-035 – Comparison Visualizations](#us-035--comparison-visualizations)
7. [US-036 – Results Summary Document](#us-036--results-summary-document)
8. [Pygame Split-Screen Demo](#pygame-split-screen-demo)
9. [Integration & Cross-Cutting Concerns](#integration--cross-cutting-concerns)
10. [Testing Strategy](#testing-strategy)
11. [Definition of Done](#definition-of-done)
12. [Risk Register](#risk-register)
13. [Suggested File Structure](#suggested-file-structure)

---

## Sprint Overview

| User Story | Title | Points | Priority |
|---|---|---|---|
| US-033 | Run Simulation with AI-Optimized Fleet | 4 | High |
| US-034 | Head-to-Head Comparison Analysis | 4 | High |
| US-035 | Comparison Visualizations | 6 | Medium |
| US-036 | Results Summary Document | 3 | Medium |
| **Total** | | **17** | |

---

## Architecture Overview

Sprint 9 mirrors the Sprint 8 experimental pipeline but loads the GA-optimal fleet instead of random fleets. The two result sets are then fed into a comparison layer that produces statistics, plots, and a report.

```
data/stations_optimal.json          outputs/baseline_results.csv
          │                                     │
          ▼                                     │
  AIFleetRunner                                 │
  (src/run_ai_fleet.py)                         │
          │                                     │
          ▼                                     ▼
  outputs/ai_results.csv  ──►  ComparisonAnalyser
  outputs/ai_response_times.csv    (src/analyze_comparison.py)
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                    Statistics        Matplotlib      Markdown/PDF
                    (t-test, SE)    4 plots → PNG    comparison_report.md
                                  src/rendering/      outputs/
                                  visualizer.py
                                          │
                                          ▼
                              PygameSplitScreenDemo
                              (src/split_screen_demo.py)
                              ENTER key toggles demo
```

All existing simulation components remain unmodified. This sprint adds new files under `src/` (following the Sprint 8 pattern of `run_baseline.py` and `analyze_baseline.py`) and new output artefacts under `outputs/`.

---

## Prerequisites & Dependencies

### From Sprints 1–8 (must be complete)

| Dependency | Required For |
|---|---|
| `data/stations_optimal.json` — GA output from Sprint 3 | US-033 fleet loading |
| `outputs/baseline_results.csv` — Sprint 8 per-run summary | US-034 comparison |
| `outputs/random_fleet_log.json` — Sprint 8 placement log | US-035 station placement plot |
| `headless_baseline.yaml` with seed strategy | US-033 seed parity |
| `src/simulation/random_fleet.py` — Sprint 8 generator | Reference for seed convention |
| `src/sim_config_loader.py` with headless env var handling | US-033 headless runs |
| `SimulationEngine` with `--headless` flag support | US-033 |
| `MetricsTracker` with `art` and `response_times` | US-033 result collection |
| `src/rendering/visualizer.py` — matplotlib module | US-035 offline plots |

### New Dependencies

```
scipy>=1.11     # scipy.stats.ttest_rel for paired t-test
pandas>=2.0     # already added in Sprint 8
```

Add `scipy` to `requirements.txt` if not already present.

### Configuration Additions

New config file `headless_ai.yaml` committed to repo root:

```yaml
# headless_ai.yaml
# Reproduces the Sprint 9 AI-optimized fleet runs exactly.
# Run with: python src/run_ai_fleet.py --headless --config headless_ai.yaml

meta:
  config_version: "1.0"
  sprint: 9
  description: "GA-optimal fleet — 10 runs, 1000 ticks each"

simulation:
  ticks: 1000
  lambda: 0.05
  num_ambulances: 5
  num_stations: 5
  service_ticks: 10

fleet:
  source: "data/stations_optimal.json"   # single fixed fleet, not randomly generated
  num_runs: 10

seeds:
  # MUST match Sprint 8 seed strategy exactly for fair comparison.
  # All randomness flows through sim_config_loader.py — no hardcoded seeds.
  event_seed: 42          # identical to headless_baseline.yaml event_seed
  ambulance_seed: 0       # reserved; matches Sprint 8 convention
  # random_seed not used — AI fleet is fixed, not randomly generated

rendering:
  headless: true
  target_fps: 0           # uncapped in headless mode
  screen_w: 1200
  screen_h: 900

output:
  results_csv:          "outputs/ai_results.csv"
  response_times_csv:   "outputs/ai_response_times.csv"
  report_md:            "outputs/comparison_report.md"
  figures_dir:          "outputs/figures/"
```

---

## US-033 – Run Simulation with AI-Optimized Fleet

**Story Points:** 4  
**Goal:** Load the fixed GA-optimal station set and run 10 headless simulations using the same event seeds as Sprint 8, producing directly comparable ART measurements.

### Loading `stations_optimal.json`

The GA output from Sprint 3 is a fixed single fleet — unlike Sprint 8 where each run used a different random fleet, all 10 AI runs use the same station positions. Only the event seed varies across runs.

```python
# src/run_ai_fleet.py

import json

def load_optimal_fleet(path: str = "data/stations_optimal.json") -> list[int]:
    """
    Load GA-optimized station node IDs from Sprint 3 output.

    Expected format:
    {
      "generation": 100,
      "fitness": 12345.6,
      "stations": [node_id_1, node_id_2, node_id_3, node_id_4, node_id_5]
    }

    Returns
    -------
    list[int]
        Ordered list of 5 node IDs representing optimal ambulance bases.

    Raises
    ------
    FileNotFoundError : if stations_optimal.json does not exist.
    KeyError          : if "stations" key is missing from JSON.
    ValueError        : if fewer than num_stations nodes are present.
    """
    with open(path, "r") as f:
        data = json.load(f)
    stations = data["stations"]
    if len(stations) < 5:
        raise ValueError(
            f"stations_optimal.json contains {len(stations)} stations; expected 5."
        )
    return stations
```

### AIFleetRunner

```python
class AIFleetRunner:
    """
    Mirrors run_baseline.py from Sprint 8 but uses a fixed fleet.
    Event seeds are IDENTICAL to Sprint 8 for fair comparison.
    All randomness flows through sim_config_loader.py — no hardcoded seeds.
    """
    def __init__(self, config: dict, graph, node_positions: dict,
                 distance_matrix, optimal_fleet: list[int]):
        self.config          = config
        self.graph           = graph
        self.node_positions  = node_positions
        self.distance_matrix = distance_matrix
        self.fleet           = optimal_fleet   # same fleet for all runs
        self.results: list[dict] = []

    def run_all(self) -> None:
        for run_id in range(self.config["num_runs"]):
            print(f"[AI Fleet] Run {run_id + 1}/{self.config['num_runs']} | "
                  f"event_seed={self.config['event_seed'] + run_id}")
            result = self._run_single(run_id)
            self.results.append(result)
            print(f"  ART: {result['art']:.2f} ticks | Events: {result['total_events']}")

    def _run_single(self, run_id: int) -> dict:
        """
        Initialise and run one complete simulation.
        event_seed offsets by run_id to produce distinct but reproducible
        event sequences — matching Sprint 8's run_baseline.py convention exactly.
        """
        engine = SimulationEngine(
            graph           = self.graph,
            node_positions  = self.node_positions,
            distance_matrix = self.distance_matrix,
            start_nodes     = self.fleet,
            ticks           = self.config["simulation_ticks"],
            lambda_rate     = self.config["lambda"],
            event_seed      = self.config["event_seed"] + run_id,
            ambulance_seed  = self.config["ambulance_seed"],
            headless        = True
        )
        engine.run()
        tracker = engine.metrics_tracker
        return {
            "run_id":         run_id,
            "fleet":          self.fleet,
            "event_seed":     self.config["event_seed"] + run_id,
            "art":            tracker.art,
            "std_dev":        tracker.std_dev,
            "total_events":   len(tracker.response_times),
            "min_rt":         min(tracker.response_times, default=0),
            "max_rt":         max(tracker.response_times, default=0),
            "response_times": tracker.response_times
        }

    def export_csv(self, path: str = "outputs/ai_results.csv") -> None:
        """Write per-run summary to CSV. Schema identical to baseline_results.csv."""

    def export_full_response_times(
            self, path: str = "outputs/ai_response_times.csv") -> None:
        """Write every individual response time with run_id label."""
```

### Output Files

| File | Contents |
|---|---|
| `outputs/ai_results.csv` | Per-run summary: run_id, event_seed, art, std_dev, total_events, min_rt, max_rt |
| `outputs/ai_response_times.csv` | Every response time with run_id (for distribution plots) |

**`ai_results.csv` schema** — identical columns to `baseline_results.csv` for easy side-by-side loading:
```
run_id, event_seed, art, std_dev, total_events, min_rt, max_rt, config_version
0, 42, 5.21, 1.44, 49, 1, 12, 1.0
1, 43, 5.08, 1.38, 47, 2, 11, 1.0
...
```

### Seed Parity Verification

Before running, the runner asserts event seed alignment with Sprint 8:

```python
def verify_seed_parity(ai_config: dict, baseline_config: dict) -> None:
    """
    Assert that event seeds are aligned between AI and baseline runs.
    Both configs must use the same event_seed base value so that
    run N in both conditions sees an identical accident sequence.
    """
    assert ai_config["event_seed"] == baseline_config["event_seed"], (
        f"event_seed mismatch: AI={ai_config['event_seed']}, "
        f"Baseline={baseline_config['event_seed']}. "
        f"Comparison will be invalid — update headless_ai.yaml to match "
        f"headless_baseline.yaml."
    )
    print("[Seed Check] ✓ event_seed matches baseline for all runs.")
```

### Tasks Breakdown

1. Implement `load_optimal_fleet()` with error handling for all three failure modes.
2. Implement `AIFleetRunner` mirroring `BaselineRunner` structure.
3. Implement seed parity verification and run it before `run_all()`.
4. Implement `export_csv()` and `export_full_response_times()` with identical schema to Sprint 8.
5. Write `src/run_ai_fleet.py` entry point with `--headless` and `--config` flags matching `src/run_baseline.py`.
6. Verify: 10 × 1000-tick headless runs complete without error; ART values are non-zero.

---

## US-034 – Head-to-Head Comparison Analysis

**Story Points:** 4  
**Goal:** Statistically quantify the improvement of the AI fleet over the random baseline using paired t-test and standard error calculation.

### ComparisonAnalyser

```python
# src/analyze_comparison.py
import numpy as np
import pandas as pd
from scipy import stats

class ComparisonAnalyser:
    def __init__(self, baseline_csv: str, ai_csv: str,
                 baseline_rt_csv: str, ai_rt_csv: str):
        self.baseline = pd.read_csv(baseline_csv)
        self.ai       = pd.read_csv(ai_csv)
        self.b_rts    = pd.read_csv(baseline_rt_csv)
        self.ai_rts   = pd.read_csv(ai_rt_csv)

    def compute_comparison(self) -> dict:
        """
        Computes all comparison metrics.

        Returns dict with:
          baseline_mean_art   : float
          ai_mean_art         : float
          absolute_improvement: float   (baseline - ai, positive = improvement)
          pct_improvement     : float   (absolute / baseline * 100)
          std_error           : float   (SE of the difference)
          t_statistic         : float
          p_value             : float
          significant         : bool    (p_value < 0.05)
          cohen_d             : float   (effect size)
          baseline_std        : float
          ai_std              : float
        """
        b_arts = self.baseline["art"].values
        a_arts = self.ai["art"].values

        # Paired t-test: each pair shares the same event seed
        t_stat, p_val = stats.ttest_rel(b_arts, a_arts)

        mean_diff = np.mean(b_arts) - np.mean(a_arts)
        se_diff   = stats.sem(b_arts - a_arts)

        # Cohen's d for paired samples
        diff      = b_arts - a_arts
        cohen_d   = np.mean(diff) / np.std(diff, ddof=1)

        return {
            "baseline_mean_art":    float(np.mean(b_arts)),
            "ai_mean_art":          float(np.mean(a_arts)),
            "absolute_improvement": float(mean_diff),
            "pct_improvement":      float(mean_diff / np.mean(b_arts) * 100),
            "std_error":            float(se_diff),
            "t_statistic":          float(t_stat),
            "p_value":              float(p_val),
            "significant":          bool(p_val < 0.05),
            "cohen_d":              float(cohen_d),
            "baseline_std":         float(np.std(b_arts, ddof=1)),
            "ai_std":               float(np.std(a_arts, ddof=1)),
            "baseline_n":           len(b_arts),
            "ai_n":                 len(a_arts)
        }

    def print_summary(self, metrics: dict) -> None:
        """Pretty-print comparison table to console."""
        print("\n" + "="*55)
        print("  HEAD-TO-HEAD COMPARISON SUMMARY")
        print("="*55)
        print(f"  Baseline Mean ART    : {metrics['baseline_mean_art']:.2f} ticks")
        print(f"  AI Mean ART          : {metrics['ai_mean_art']:.2f} ticks")
        print(f"  Absolute Improvement : {metrics['absolute_improvement']:.2f} ticks")
        print(f"  % Improvement        : {metrics['pct_improvement']:.1f}%")
        print(f"  Std Error (diff)     : {metrics['std_error']:.3f}")
        print(f"  t-statistic          : {metrics['t_statistic']:.3f}")
        print(f"  p-value              : {metrics['p_value']:.4f}")
        sig = "YES ✓" if metrics["significant"] else "NO ✗"
        print(f"  Significant (p<0.05) : {sig}")
        print(f"  Cohen's d            : {metrics['cohen_d']:.3f}")
        print("="*55 + "\n")
```

### Statistical Notes

**Why paired t-test?** Each run pair (baseline run 0 vs AI run 0) uses the same event seed, making them paired observations. A paired test removes between-run event variance from the error term, giving a more sensitive test of the fleet effect.

**Cohen's d interpretation:**
- d < 0.2: negligible effect
- 0.2 ≤ d < 0.5: small effect
- 0.5 ≤ d < 0.8: medium effect
- d ≥ 0.8: large effect

Document the Cohen's d value and interpretation in the report regardless of p-value significance.

**Response time definition:** Spawn Tick → Arrival Tick (per README and Sprint 8 convention). This definition is stated explicitly in the report methodology section.

### Tasks Breakdown

1. Implement `ComparisonAnalyser` with `compute_comparison()`.
2. Implement `print_summary()` for console output.
3. Export comparison metrics to `outputs/comparison_metrics.json` for use by report generator.
4. Write `src/analyze_comparison.py` entry point (mirrors `src/analyze_baseline.py` pattern).

---

## US-035 – Comparison Visualizations

**Story Points:** 6  
**Goal:** Produce four publication-quality Matplotlib plots (offline, saved as PNG) and implement the Pygame split-screen demo mode.

### Plot 1 — Side-by-Side ART Distributions

```
Type:   Overlapping histograms (or KDE curves)
X axis: ART (ticks)
Y axis: Density / frequency
Series: Baseline (red, semi-transparent) vs AI (blue, semi-transparent)
Extras: Vertical dashed mean lines for each series
        Legend with mean values annotated
        Significance marker if p < 0.05: "* p < 0.05" in top-right corner
Output: outputs/figures/comparison_art_distribution.png
```

### Plot 2 — Time-Series Response Times (Per Run)

```
Type:   Dual line plot
X axis: Run index (0–9)
Y axis: Mean ART per run
Series: Baseline (red circles) vs AI (blue squares)
Extras: Error bars = ±1 std dev per run
        Horizontal dashed lines for overall means
        Shaded band between the two series
Output: outputs/figures/comparison_art_timeseries.png
```

### Plot 3 — Demand Coverage Heatmaps

```
Type:   Side-by-side heatmaps on the Model Town map background
Left:   Baseline fleet — coverage decay from random station positions
Right:  AI fleet — coverage decay from GA-optimal positions
Method: For each node in graph, colour = distance to nearest station
        (from distance_matrix, O(1) lookup)
        Colour scale: green (close) → yellow → red (far)
        Station positions overlaid as stars
Output: outputs/figures/comparison_coverage_heatmap.png

Implementation note:
  Use node pixel positions from node_positions.json to scatter-plot
  each node coloured by its nearest-station distance.
  map_bg.png used as background via plt.imshow().
  All plots implemented in src/rendering/visualizer.py.
```

### Plot 4 — Station Placement Comparison

```
Type:   Map with overlaid markers (two subplots or single plot with legend)
Background: map_bg.png via plt.imshow()
Markers:
  - Random stations (10 runs × 5 stations = up to 50 points, semi-transparent gray)
    showing the spread of random placements
  - GA-optimal stations (5 points, solid blue stars, larger)
  - Voronoi boundary lines for optimal fleet (optional overlay)
Output: outputs/figures/comparison_station_placement.png

Note: The 50 random station positions are loaded from
      outputs/random_fleet_log.json (saved in Sprint 8).
```

### Shared Plot Styling Conventions

All four plots follow these conventions for visual consistency and are implemented in `src/rendering/visualizer.py` alongside the existing Sprint 8 baseline plots:

```python
STYLE = {
    "baseline_colour": "#E74C3C",    # red
    "ai_colour":       "#2980B9",    # blue
    "figsize":         (10, 6),
    "dpi":             150,
    "font_title":      14,
    "font_axis":       11,
    "grid_alpha":      0.3,
    "significance_marker": "* p < 0.05"
}
```

All plots:
- Include title, axis labels, and legend
- Use `plt.tight_layout()` before saving
- Saved with `plt.savefig(path, dpi=150, bbox_inches="tight")`
- Never use `plt.show()` — offline analysis only

### Pygame Split-Screen Demo

The split-screen demo runs two `SimulationEngine` instances side by side in a single Pygame window, showing both fleets running simultaneously under identical event conditions.

**Activation:** Press **ENTER** from the main simulation window, or launch directly:
```bash
python src/split_screen_demo.py
```

#### Window Layout

```
┌─────────────────────────────────────────────────┐
│            RESQ-GRAPH: FLEET COMPARISON          │
├────────────────────────┬────────────────────────┤
│                        │                        │
│   RANDOM FLEET         │   AI-OPTIMAL FLEET     │
│   (Baseline)           │   (GA-Optimized)       │
│                        │                        │
│   [map + ambulances]   │   [map + ambulances]   │
│   [accidents]          │   [accidents]          │
│   [paths]              │   [paths]              │
│                        │                        │
├────────────────────────┴────────────────────────┤
│  Tick: 342   Baseline ART: 8.12   AI ART: 5.34  │
│  SPACE: pause   ESC: quit   ENTER: toggle demo   │
└─────────────────────────────────────────────────┘
```

**Window dimensions:** 2400 × 950 px (two 1200 × 900 panels + 50 px bottom HUD bar)

#### Implementation Approach

```python
# experiments/split_screen_demo.py

class SplitScreenDemo:
    def __init__(self, config: dict, graph, node_positions: dict,
                 distance_matrix, baseline_fleet: list[int],
                 optimal_fleet: list[int]):
        self.screen = pygame.display.set_mode((2400, 950))

        # Two separate surfaces — one per panel
        self.left_surface  = pygame.Surface((1200, 900))
        self.right_surface = pygame.Surface((1200, 900))

        # Two independent engines sharing the same event seed
        shared_event_seed = config["master_seed"] * 100   # run 0
        self.engine_left  = SimulationEngine(
            ..., start_nodes=baseline_fleet, event_seed=shared_event_seed
        )
        self.engine_right = SimulationEngine(
            ..., start_nodes=optimal_fleet, event_seed=shared_event_seed
        )

        # Two renderers, each targeting their own surface
        self.renderer_left  = PygameRenderer(self.left_surface,  node_positions)
        self.renderer_right = PygameRenderer(self.right_surface, node_positions)

    def run(self) -> None:
        clock   = pygame.time.Clock()
        paused  = False
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused

            if not paused:
                self.engine_left.tick()
                self.engine_right.tick()

            # Render each engine to its surface
            self.renderer_left.draw(self.engine_left.state,
                                    self.engine_left.ambulances)
            self.renderer_right.draw(self.engine_right.state,
                                     self.engine_right.ambulances)

            # Blit both surfaces onto main screen
            self.screen.blit(self.left_surface,  (0,   0))
            self.screen.blit(self.right_surface, (1200, 0))

            # Bottom HUD bar
            self._draw_comparison_hud()

            pygame.display.flip()
            clock.tick(60)

    def _draw_comparison_hud(self) -> None:
        """Bottom 50px bar: tick, baseline ART, AI ART, key hints."""
```

#### Key Design Constraints

- Both engines must receive the **same event seed** so accident patterns are identical — this makes the visual comparison meaningful.
- The two `SimulationEngine` instances are completely independent. They share no mutable state.
- The existing `PygameRenderer` is used unmodified — it simply targets a different `pygame.Surface`.
- The demo runs one `SimulationEngine.tick()` per loop iteration (not `run()`) so both engines advance in lockstep.
- If `PygameRenderer` was not designed to accept a surface parameter (currently targets `screen` directly), a minimal refactor is needed: pass `surface` as a constructor argument and replace `self.screen` references. Document this in the tasks.

#### Tasks Breakdown (US-035)

1. Add all four comparison plot functions to `src/rendering/visualizer.py` (alongside existing Sprint 8 plots).
2. Implement shared styling constants and `_apply_style()` helper in `visualizer.py`.
3. Implement coverage heatmap using `data/node_positions.json` + `data/distance_matrix.npy`.
4. Implement station placement plot loading from `outputs/random_fleet_log.json`.
5. Refactor `PygameRenderer.__init__` to accept `surface` parameter (if needed — check `pygame_renderer.py` first).
6. Implement `SplitScreenDemo` class in `src/split_screen_demo.py` with dual-engine, dual-surface architecture.
7. Implement `_draw_comparison_hud()` bottom bar.
8. Verify ENTER key launches demo from `src/main.py`.

---

## US-036 – Results Summary Document

**Story Points:** 3  
**Goal:** Auto-generate a comprehensive Markdown report (and optional PDF) from all Sprint 9 outputs.

### Report Structure

```markdown
# ResQ-Graph: AI Fleet vs Baseline — Comparison Report

**Generated:** {timestamp}
**Config Version:** 1.0
**Sprint:** 9

---

## Executive Summary

The GA-optimized fleet achieved a mean Average Response Time of **X.XX ticks**,
compared to **X.XX ticks** for the random baseline — a **XX.X% improvement**
(p = 0.XXXX, Cohen's d = X.XX).

| Metric | Baseline | AI Fleet | Improvement |
|---|---|---|---|
| Mean ART | X.XX | X.XX | X.XX (XX%) |
| Std Dev (ART) | X.XX | X.XX | — |
| Total Events | N | N | — |
| Fastest Response | N | N | — |
| Slowest Response | N | N | — |

---

## Methodology

- **Simulation ticks per run:** 1000
- **Event arrival rate (λ):** 0.05
- **Number of ambulances:** 5
- **Number of runs:** 10 (each)
- **Event seeds:** Identical across both conditions (4200–4209)
- **Baseline fleet:** Random placement (seed = master_seed + run_id)
- **AI fleet:** Fixed GA-optimal stations from `data/stations_optimal.json`
- **Response time definition:** Spawn Tick → Arrival Tick
- **Statistical test:** Two-tailed paired t-test (paired by event seed)

---

## Detailed Results

### Per-Run ART Values

| Run | Event Seed | Baseline ART | AI ART | Difference |
|---|---|---|---|---|
| 0 | 4200 | X.XX | X.XX | X.XX |
...
| **Mean** | — | **X.XX** | **X.XX** | **X.XX** |

### Statistical Results

| Statistic | Value |
|---|---|
| Absolute Improvement | X.XX ticks |
| Percentage Improvement | XX.X% |
| Standard Error | X.XXX |
| t-statistic | X.XXX |
| p-value | X.XXXX |
| Significant (p < 0.05) | Yes / No |
| Cohen's d | X.XXX (small/medium/large) |

---

## Visualizations

![ART Distribution](plots/comparison_art_distribution.png)
![ART Time Series](plots/comparison_art_timeseries.png)
![Coverage Heatmap](plots/comparison_coverage_heatmap.png)
![Station Placement](plots/comparison_station_placement.png)

---

## Caveats & Limitations

- Baseline uses different fleet per run; AI uses the same fleet for all runs.
  This is intentional (AI has a fixed solution) but means the comparison is
  AI policy vs average random policy, not AI vs a single random policy.
- Response time = Spawn Tick → Arrival Tick. Queue wait time (spawn → dispatch)
  and travel time (dispatch → scene) are not separated in this analysis.
- Traffic dynamics (Sprint 7) affect both fleets equally; no fleet-specific
  advantage from traffic modelling is expected or tested here.
- HDBSCAN rebalancing is active for both fleets during runs.
- Results are specific to the Model Town, Lahore simulation environment.

---

## Conclusions

{auto-generated paragraph based on significance and effect size}
```

### PDF Generation (Optional)

If `pandoc` is available on the system, the report generator attempts PDF conversion:

```python
import subprocess, shutil

def export_pdf(md_path: str, pdf_path: str) -> None:
    if shutil.which("pandoc"):
        subprocess.run([
            "pandoc", md_path, "-o", pdf_path,
            "--pdf-engine=xelatex",
            "-V", "geometry:margin=2cm"
        ], check=True)
        print(f"[Report] PDF saved: {pdf_path}")
    else:
        print("[Report] pandoc not found — PDF skipped. Markdown report available.")
```

PDF is a bonus; the Markdown report is the primary deliverable.

### Tasks Breakdown

1. Implement `ComparisonReportGenerator` in `src/analyze_comparison.py` (alongside `ComparisonAnalyser`).
2. Implement `generate_markdown()` with all six sections auto-populated from metrics dict.
3. Implement `export_pdf()` with graceful fallback if pandoc absent.
4. Verify all four plot images embedded with paths relative to `outputs/`.
5. Verify report renders correctly in GitHub Markdown preview.

---

## Integration & Cross-Cutting Concerns

### Seed Parity Is The Fairness Guarantee

The entire validity of the comparison rests on event seed parity. Before the comparison report is generated, the analyser should assert:

```python
assert list(baseline["event_seed"]) == list(ai["event_seed"]), \
    "Event seeds do not match — comparison results are invalid."
```

This assertion runs automatically in `ComparisonAnalyser.__init__`.

### What This Sprint Does NOT Modify

Following the established convention that experiments are wrappers around the existing engine:

- `src/simulation/simulation_engine.py` — unchanged
- `src/rendering/pygame_renderer.py` — minimal refactor only if surface param needed for split-screen
- `src/simulation/dispatcher.py`, `ambulance.py`, `metrics_tracker.py` — all unchanged
- `sim_config.yaml` (default profile) — unchanged

### The `stations_optimal.json` Format Assumption

The Sprint 3 GA output format is assumed to be:
```json
{
  "generation": 100,
  "fitness": 12345.6,
  "stations": [node_id_1, node_id_2, node_id_3, node_id_4, node_id_5]
}
```

If the actual format differs, `load_optimal_fleet()` handles it with a clear `KeyError` and message. Check the Sprint 3 output before running US-033.

### Coverage Heatmap Using Distance Matrix

The coverage heatmap (Plot 3) uses the pre-computed `data/distance_matrix.npy` for O(1) nearest-station distance lookups — consistent with the `assignment.py` convention from the README. Never compute Euclidean distance for this plot; always use the graph distance matrix.

```python
def nearest_station_distance(node_idx: int, station_indices: list[int],
                              distance_matrix: np.ndarray) -> float:
    return min(distance_matrix[node_idx, s] for s in station_indices)
```

---

## Testing Strategy

### US-033 — AI Fleet Runner Tests

| Test | Assertion |
|---|---|
| Fleet loads correctly | `len(load_optimal_fleet()) == 5` |
| FileNotFoundError | Raised if `stations_optimal.json` absent |
| Seed parity | `verify_seed_parity()` passes with matching configs |
| Seed mismatch | `verify_seed_parity()` raises `AssertionError` |
| 100-tick headless run | Completes; `result["art"] > 0` |
| CSV schema | `ai_results.csv` columns match `baseline_results.csv` |

### US-034 — Comparison Analyser Tests

| Test | Assertion |
|---|---|
| Perfect improvement | Synthetic data where AI ART = baseline ART - 3: `pct_improvement ≈ 30%` |
| No improvement | Identical ART arrays → p-value > 0.05, `significant == False` |
| Event seed assertion | Mismatched seeds raise AssertionError in `__init__` |
| Cohen's d sign | Positive when AI ART < baseline ART |
| t-test direction | `t_statistic > 0` when baseline ART > AI ART |

### US-035 — Visualization Tests

| Test | Assertion |
|---|---|
| All 4 PNGs created | Files exist in `outputs/figures/` after `generate_all_plots()` |
| Coverage heatmap nodes | Uses distance matrix, not Euclidean |
| Station placement | `outputs/random_fleet_log.json` loaded; 10 × 5 = 50 points plotted |
| Split-screen init | Window opens at 2400 × 950 without error (dummy SDL) |
| Dual engine tick | Both engines advance same tick count after N loop iterations |

### US-036 — Report Tests

| Test | Assertion |
|---|---|
| MD file created | `comparison_report.md` exists and is non-empty |
| Plot links present | All 4 image references present in markdown |
| Significance language | "significant" / "not significant" matches `metrics["significant"]` |
| PDF optional | No exception raised when pandoc absent |

---

## Definition of Done

- All acceptance criteria from both the original and Pygame-updated specification are met.
- 10 × 1000-tick AI fleet headless runs complete without error.
- `ai_results.csv` and `ai_response_times.csv` present in `outputs/`.
- Seed parity assertion passes before any comparison is run.
- All four Matplotlib plots saved as PNG in `outputs/plots/`.
- Pygame split-screen demo opens with ENTER; both fleets visible with shared tick counter.
- `comparison_report.md` auto-generated with all sections populated.
- Statistical results (t-test, Cohen's d) documented in report.
- `headless_ai.yaml` committed to repo root.
- Unit tests pass; seed parity test confirms identical event sequences.
- Sprint board card moved to Done.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `stations_optimal.json` format differs from assumption | Medium | High | Check format before sprint; update `load_optimal_fleet()` if needed |
| AI ART not better than baseline (null result) | Low | Medium | Document as valid scientific result; check GA convergence from Sprint 3 |
| `PygameRenderer` not surface-parameterised | Medium | Medium | Refactor constructor early in sprint; surface param is a 1-line change |
| Split-screen window too large for dev monitor | Low | Low | Make window size configurable; default to 1800 × 700 as fallback |
| pandoc not available for PDF | Medium | Low | PDF is optional; Markdown is primary deliverable |
| Coverage heatmap slow for large graph | Low | Medium | Vectorise with `np.min(distance_matrix[node_idx, station_indices])` |
| Comparison invalid if Sprint 8 used different response time definition | Low | High | Assert definition in report methodology; cross-check with MetricsTracker |

---

## Suggested File Structure

```
resq-graph/
├── data/
│   ├── model_town.graphml             # Unchanged
│   ├── node_positions.json            # Unchanged
│   ├── map_bg.png                     # Unchanged
│   ├── distance_matrix.npy            # Unchanged
│   └── stations_optimal.json          # From Sprint 3 — read-only input
├── outputs/
│   ├── figures/                       # ALL matplotlib plots go here
│   │   ├── [Sprint 8 baseline plots]  # Already present
│   │   ├── comparison_art_distribution.png    # NEW
│   │   ├── comparison_art_timeseries.png      # NEW
│   │   ├── comparison_coverage_heatmap.png    # NEW
│   │   └── comparison_station_placement.png   # NEW
│   ├── baseline_results.csv           # From Sprint 8 — read-only input
│   ├── baseline_report.md             # From Sprint 8 — read-only input
│   ├── random_fleet_log.json          # From Sprint 8 — read-only input
│   ├── ai_results.csv                 # NEW: per-run AI summary
│   ├── ai_response_times.csv          # NEW: all AI response times
│   ├── comparison_metrics.json        # NEW: t-test results, Cohen's d, etc.
│   ├── comparison_report.md           # NEW: auto-generated report
│   └── comparison_report.pdf          # NEW: optional pandoc output
├── src/
│   ├── main.py                        # UPDATED: ENTER key launches split-screen demo
│   ├── config.py                      # Unchanged
│   ├── sim_config_loader.py           # Unchanged
│   ├── run_baseline.py                # From Sprint 8 — unchanged
│   ├── analyze_baseline.py            # From Sprint 8 — unchanged
│   ├── run_ai_fleet.py                # NEW: US-033 headless AI batch runner
│   ├── analyze_comparison.py          # NEW: US-034 + US-036 analyser + report generator
│   ├── split_screen_demo.py           # NEW: US-035 Pygame split-screen demo
│   ├── astar.py                       # Unchanged
│   ├── distance_matrix.py             # Unchanged
│   ├── intelligence/
│   │   ├── hdbscan.py                 # Unchanged
│   │   └── demand_clustering.py       # Unchanged
│   ├── rendering/
│   │   ├── pygame_renderer.py         # UPDATED: surface param (if needed for split-screen)
│   │   └── visualizer.py             # UPDATED: 4 new comparison plot functions added
│   └── simulation/
│       ├── ambulance.py               # Unchanged
│       ├── assignment.py              # Unchanged
│       ├── dispatcher.py              # Unchanged
│       ├── event_spawner.py           # Unchanged
│       ├── metrics_tracker.py         # Unchanged
│       ├── random_fleet.py            # From Sprint 8 — unchanged
│       ├── sim_logger.py              # Unchanged
│       ├── simulation_engine.py       # Unchanged
│       └── traffic.py                 # Unchanged
├── tests/
│   ├── test_run_ai_fleet.py           # NEW
│   ├── test_analyze_comparison.py     # NEW
│   └── test_split_screen_demo.py      # NEW
├── headless_ai.yaml                   # NEW: committed to repo root
├── headless_baseline.yaml             # From Sprint 8 — unchanged
├── sim_config.yaml                    # Unchanged
└── README.md                          # UPDATED: Sprint 9 run instructions
```

---

*Plan prepared for Sprint 9 — Week 9. Follows the file layout established in the Sprint 8 README. All new scripts go in `src/` (not `experiments/`). All plots go in `outputs/figures/`. Sprint 8 files `random_fleet_log.json`, `baseline_results.csv`, and `headless_baseline.yaml` are read-only inputs. Depends on Sprint 3 deliverable: `data/stations_optimal.json`.*