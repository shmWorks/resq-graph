
## SPRINT PLAN — AUDIT VALIDATED

> **Done: S1–S11 (11/14 schedule sprints complete, verified by codebase).** S12–S14 not started.
> **This SPEC adds custom scope S-A/B/C that runs parallel to S12.** All FRs below belong to S-A, S-B, S-C.

`✓`=done `→`=next `·`=not started

| Sprint | Goal | Key Deliverables | Status |
|---|---|---|---|
| S1 | Map + graph env | `model_town.graphml`, `distance_matrix.npy` | ✓ |
| S2 | A* pathfinding | `astar.py`, `draw_path.py` | ✓ |
| S3 | GA station optimizer | `genetic_algorithm.py`, `fitness.py`, convergence plot | ✓ |
| S4 | Ambulance agents + sim loop | `ambulance.py`, `event_spawner.py`, `pygame_renderer.py` | ✓ |
| S5 | Dispatcher + ART metrics | `dispatcher.py`, `assignment.py`, `metrics_tracker.py` | ✓ |
| S6 | HDBSCAN hotspot rebalancing | `hdbscan.py`, `demand_clustering.py` | ✓ |
| S7 | Traffic dynamics + rerouting | `traffic.py`, `astar_traffic.py` | ✓ |
| S8 | Headless baseline runner | `run_baseline.py`, `random_fleet.py` | ✓ |
| S9 | AI fleet + split-screen | `run_ai_fleet.py`, `split_screen_demo.py`, `analyze_comparison.py` | ✓ |
| S10 | Sensitivity analysis | `analyze_baseline.py`, parameter sweep scripts | ✓ |
| S11 | Integration + regression tests | `tests/integration/`, `tests/regression/`, edge cases | ✓ |
| **S-A** | **CCH routing engine** | `src/routing/cch.py`, `router.py`, `dstar_lite.py` | → |
| **S-B** | **Predictive traffic + ART→seconds** | `predictive_traffic.py`, metrics augment | → |
| **S-C** | **Constraint dispatcher + self-heal + decision log** | dispatcher augment, `decision_log.py` | → |
| S12 | Profiling + scaling (schedule) | cProfile output, 10k-tick run, dirty-rect renderer | · |
| S13 | Docs + code quality | Docstrings, arch diagram, PEP8 | · |
| S14 | Final delivery | Report, slides, demo, submission | · |

---

## DECISION LOG

| Decision         | Choice    | Rejected     | Hard Reason                                                  |
| ---------------- | --------- | ------------ | ------------------------------------------------------------ |
| Routing algo     | CCH       | CRP          | CRP needs graph partitioning; CCH needs only degree ordering |
| Local reroute    | D\*-Lite  | corridor-A\* | D*-Lite reuses prior search tree; corridor-A* discards it    |
| Integration mode | Alongside | Replace      | Cold-replace causes simultaneous regression in 3 call sites  |
| Online ML        | River lib | from-scratch | Spec allows River; from-scratch shifts sprint focus          |
| ART unit         | seconds   | ticks        | Ticks are uninterpretable; 1 tick ≈ 8.85s real-world        |

---

## GRAPH FACTS (authoritative, do not recompute)

```
Nodes=798  Edges=1110  mean_edge=98.2m  min=1.6m  max=1386.5m
speed=1.0 node/tick  TICK_RATE=1s/tick  TICK_DURATION_S = 98.2/11.1 = 8.845s
SCENE_SERVICE_TICKS=10  AMBULANCE_SPEED_MPS=11.1  (40km/h)
```

---

## NEW FILES (create)

```
src/routing/__init__.py
src/routing/cch.py
src/routing/dstar_lite.py
src/routing/router.py
src/routing/decision_log.py
src/intelligence/predictive_traffic.py
tests/unit/test_cch.py
tests/unit/test_dstar_lite.py
tests/unit/test_constraint_dispatcher.py
tests/integration/test_router.py
tests/regression/test_simulation_regression.py
DECISIONS.md
```

## EXISTING CALL SITES — must migrate to Router (3 locations)

```python
# dispatcher.py:assign_task() line ~211
path = astar_traffic(self.graph, ambulance.current_location, event.location, self.traffic)

# dispatcher.py:rebalance_fleet() line ~285 and ~347 (2 occurrences)
path = astar_traffic(self.graph, best_amb.current_location, hotspot.centroid_node, self.traffic)
path = astar_traffic(self.graph, amb.current_location, amb.home_node, self.traffic)

# ambulance.py:navigate() line ~55 — fallback only, keep as-is (internal fallback)
path = astar(self.graph, self.current_location, destination)
```
Replace first 3 with `self.router.query(start, goal)`. Leave `ambulance.navigate()` fallback untouched.

## EXISTING TESTS — must stay GREEN (do not break)

```
tests/test_ambulance.py
tests/test_assignment.py
tests/test_congestion_rerouting.py
tests/test_demand_clustering.py
tests/test_dispatcher_brain.py
tests/test_event_spawner.py
tests/test_hdbscan.py
tests/test_hotspot_detection.py
tests/test_map_config.py
tests/test_metrics_tracker.py
tests/test_rebalancing.py
tests/test_sim_config_loader.py
tests/test_sim_logger.py
tests/test_simulation_engine.py
tests/test_traffic.py
tests/integration/test_full_simulation.py
tests/integration/test_ga_pipeline.py
tests/integration/test_pygame_headless.py
tests/regression/test_regression_suite.py
```

## EXISTING ART BASELINE (for regression target)
Run `python src/run_baseline.py --headless --config headless_baseline.yaml` on seeds [42,137,999] BEFORE any changes. Record `art` from `outputs/metrics_summary.csv`. This is the A*-baseline. New system must achieve `art_seconds <= 0.70 * baseline_art_seconds`.



## MODIFIED FILES (augment only, do not break existing tests)

```
src/config.py           ← add constants block below
src/simulation/dispatcher.py   ← add 3 methods, augment assign_task + reroute calls
src/simulation/metrics_tracker.py  ← add art_seconds property + seconds conversion
src/simulation/ambulance.py    ← add position_history deque field
src/simulation/simulation_engine.py ← wire Router + PredictiveTrafficEngine into _tick
```

UNTOUCHED (do not modify)

```
src/astar.py  src/astar_traffic.py  src/intelligence/*  src/rendering/*
src/simulation/traffic.py  src/simulation/assignment.py  src/simulation/event_spawner.py
```

---

## CONFIG ADDITIONS (src/config.py — append)

```python
AMBULANCE_SPEED_MPS          = 11.1    # 40 km/h
TICK_DURATION_SECONDS        = None    # set at startup: mean_edge_m / AMBULANCE_SPEED_MPS
CCH_CUSTOMIZATION_DELTA      = 0.1    # mean multiplier Δ threshold → trigger re-customization
DSTAR_SEARCH_RADIUS          = 50     # max hops for D*-Lite local subgraph
OPTIMIZATION_INTERVAL        = 5      # ticks between global re-assignment pass
REASSIGNMENT_GAIN_THRESHOLD  = 0.40   # min fleet ART gain fraction to approve swap
MAX_RESPONSE_TIME_SECONDS    = 420.0  # 7-min hard cap
PREDICTION_HORIZON           = 5      # ticks-ahead target for River model
PREDICTIVE_MODE              = True
TICKS_PER_DAY                = 1000
STUCK_DETECTION_WINDOW       = 5      # identical positions = STUCK
DECISION_LOG_FLUSH_INTERVAL  = 50
```

`TICK_DURATION_SECONDS` computed once at engine init:

```python
lengths = [d.get('length', 98.2) for _, _, d in graph.edges(data=True)]
TICK_DURATION_SECONDS = (sum(lengths)/len(lengths)) / AMBULANCE_SPEED_MPS
```

---

## FR-01: src/routing/cch.py

**Public interface (only these methods are public):**

```python
class CCH:
    def __init__(self, graph: nx.MultiGraph) -> None
    def preprocess(self) -> None                          # call once at startup; < 2s
    def customize(self, weight_fn: Callable[[int,int], float]) -> None  # < 200ms
    def query(self, s: int, t: int) -> list[int] | None  # bidirectional Dijkstra on CH; < 5ms
```

**Preprocessing (inside `preprocess`):**

1. Order vertices by degree ascending → `self.order: list[int]`, `self.rank: dict[int,int]`.
2. For each vertex v in order: find all pairs (u, w) where u→v→w and removing v would lose the shortest path. Insert shortcut edge `(u,w)` with `weight = dist(u,v) + dist(v,w)`.
3. Store: `self.shortcuts: dict[tuple[int,int], float]`, `self.up_graph`, `self.down_graph` (subgraphs respecting rank).

**Customization (inside `customize`):**

- Re-weight every original edge and every shortcut using `weight_fn(u,v)`.
- Update `self.up_graph` and `self.down_graph` edge weights in-place.
- `weight_fn` signature: `(u: int, v: int) -> float`. Caller provides `TrafficModel.get_weight` or predictive wrapper.

**Query (inside `query`):**

- Bidirectional Dijkstra: forward search on `up_graph` from s, backward on `down_graph` from t.
- Meeting point = node with min `d_fwd[v] + d_bwd[v]`.
- Reconstruct full path by unpacking shortcuts via `self.shortcut_mid: dict[tuple,int]`.
- Return `None` if no path. Never raise.

**Allowed imports**: `networkx` (graph input only), `numpy`, `heapq`, `collections`.
**Forbidden**: `nx.dijkstra_path`, `nx.astar_path`, any nx routing function.

---

## FR-02: src/routing/dstar_lite.py

**Public interface:**

```python
class DStarLite:
    def initialize(self, subgraph: nx.Graph, start: int, goal: int,
                   weight_fn: Callable[[int,int], float]) -> None
    def get_path(self) -> list[int]
    def update_edge(self, u: int, v: int, new_weight: float) -> None  # new_weight=inf → blocked
    def advance(self) -> int  # consume next node; update start internally
```

- Operates on subgraph of radius `DSTAR_SEARCH_RADIUS` hops around current ambulance position (caller extracts subgraph via `nx.ego_graph`).
- `update_edge` repairs search tree locally in O(k log V), k = affected nodes. Does NOT restart.
- `get_path` returns current best path from `start` to `goal` within subgraph.
- If `goal` unreachable in subgraph: return `[]`. Caller falls back to `CCH.query`.

---

## FR-03: src/routing/router.py

**Public interface:**

```python
class Router:
    def __init__(self, graph: nx.MultiGraph, distance_matrix: np.ndarray,
                 node_index: dict, traffic: TrafficModel | None) -> None
    def query(self, s: int, t: int) -> list[int] | None
    def get_eta_seconds(self, path: list[int]) -> float
    def report_obstacle(self, u: int, v: int, amb_id: int) -> list[int] | None
    def trigger_customization(self) -> None
    def tick(self, current_tick: int) -> None  # checks if customization needed
```

- `query`: CCH → fallback `distance_matrix` O(1) lookup → None.
- `get_eta_seconds`: `sum(graph[path[i]][path[i+1]] edge_length for i) / AMBULANCE_SPEED_MPS`.
- `report_obstacle`: sets edge weight to inf in DStarLite instance for `amb_id`; returns repaired path. Creates DStarLite instance for `amb_id` if not exists.
- `trigger_customization`: calls `CCH.customize(predictive_weight_fn if PREDICTIVE_MODE else traffic.get_weight)`.
- `tick`: tracks rolling mean of `traffic.edge_multipliers`; calls `trigger_customization()` if delta > `CCH_CUSTOMIZATION_DELTA`.
- Owns: `dict[int, DStarLite]` keyed by `amb_id`. One DStarLite per in-transit ambulance.

**Fallback chain**: CCH → distance_matrix → None. Never raises.

---

## FR-04: src/routing/decision_log.py

```python
class DecisionLog:
    def log(self, tick: int, tick_s: float, decision_type: str,
            amb_id: int, event_id: int, reason: str,
            path_before: list[int], path_after: list[int],
            eta_before_s: float, eta_after_s: float) -> None
    def flush(self) -> None
```

- `decision_type` ∈ `{"DISPATCH","REROUTE","REASSIGNMENT","SELF_HEAL","OBSTACLE"}`.
- Writes JSONL to `outputs/decisions.jsonl`. Buffered; `flush()` called every `DECISION_LOG_FLUSH_INTERVAL` ticks.
- Never raises. If file write fails: log warning, discard buffer, continue.

---

## FR-05: src/intelligence/predictive_traffic.py

```python
class PredictiveTrafficEngine:
    def __init__(self, graph: nx.MultiGraph, traffic: TrafficModel,
                 horizon: int = PREDICTION_HORIZON) -> None
    def tick(self, current_tick: int) -> None  # learn from last tick; update predictions
    def predicted_weight(self, u: int, v: int) -> float  # clamp to [1.0, max_multiplier]
```

- One `river.linear_model.LinearRegression` per edge (keyed `frozenset({u,v})`).
- Feature vector per edge per tick: `[current_mult, tick % TICKS_PER_DAY, nearby_events_count, rolling_mean_5]`.
- `rolling_mean_5`: `collections.deque(maxlen=5)` per edge, tracks last 5 multiplier values.
- `nearby_events_count`: edges within `TrafficModel.influence_radius` of any active event midpoint.
- `tick()`:
  1. For each edge: record `actual = traffic.get_multiplier(u,v)` into history.
  2. If `len(history) > horizon`: call `model.learn_one(features_at_t_minus_horizon, actual)`.
  3. Update `rolling_mean_5` with `actual`.
- `predicted_weight(u,v)`: `base_length * clamp(model.predict_one(features), 1.0, max_mult)`.
- If River unavailable (ImportError): `predicted_weight` returns `traffic.get_weight(u,v)` (transparent fallback, no crash).

---

## FR-06: dispatcher.py augmentations

### 6a. assign_task — replace routing call

```python
# BEFORE:
path = astar_traffic(self.graph, ambulance.current_location, event.location, self.traffic)
# AFTER:
path = self.router.query(ambulance.current_location, event.location)
```

Same for `rebalance_fleet` (2 call sites). Same for `_reroute_ambulance`.

### 6b. Add \_run_global_optimization(current_tick)

Called in `tick()` at step 2.5 (after on-scene check, before assign):

```
if current_tick % OPTIMIZATION_INTERVAL == 0:
    self._run_global_optimization(current_tick)
```

Logic (pseudocode — implement exactly):

```
for each amb A where state == IN_TRANSIT and assigned_task == E_A:
    T_A_remaining = router.get_eta_seconds(router.query(A.current_location, E_A.location))
    if T_A_remaining > MAX_RESPONSE_TIME_SECONDS: continue  # already failing, skip

    for each event E_B where E_B != E_A and E_B.assigned_ambulance_id is None:
        best_idle = assign_nearest_idle(E_A, get_idle_ambulances(), distance_matrix, node_index)
        if best_idle is None: continue

        T_B_via_A   = router.get_eta_seconds(router.query(A.current_location, E_B.location))
        T_A_replace = router.get_eta_seconds(router.query(best_idle.current_location, E_A.location))

        if T_A_replace > MAX_RESPONSE_TIME_SECONDS: continue  # hard gate
        gain = (T_A_remaining - T_B_via_A) / T_A_remaining
        if gain < REASSIGNMENT_GAIN_THRESHOLD: continue

        # All gates passed → execute swap
        assign_task(A, E_B, current_tick)
        assign_task(best_idle, E_A, current_tick)
        decision_log.log(tick=current_tick, tick_s=current_tick*TICK_DURATION_SECONDS,
                         decision_type="REASSIGNMENT", amb_id=A.id, event_id=E_B.id,
                         reason=f"gain={gain:.2f},T_replace={T_A_replace:.0f}s",
                         path_before=A.current_path, path_after=router.query(A.current_location, E_B.location),
                         eta_before_s=T_A_remaining, eta_after_s=T_B_via_A)
        break  # one swap per ambulance per optimization pass
```

### 6c. Add self-heal to \_check_rerouting

```
for amb in ambulances where state == IN_TRANSIT:
    amb.position_history.append(amb.current_location)
    if len(amb.position_history)==STUCK_DETECTION_WINDOW and len(set(amb.position_history))==1:
        # STUCK
        task = amb.assigned_task
        amb.state = IDLE; amb.assigned_task = None; amb.current_path = []
        task.assigned_ambulance_id = None; task.priority += 1
        active_events.append(task)  # re-queue
        decision_log.log(..., decision_type="SELF_HEAL", ...)
```

---

## FR-07: metrics_tracker.py augmentations

```python
@property
def art_seconds(self) -> float:
    return self.art * TICK_DURATION_SECONDS  # TICK_DURATION_SECONDS from config

def record_response(self, ...) -> None:
    # existing tick-based rt stays for backward compat
    # add: rt_seconds = (arrival_tick - spawn_tick) * TICK_DURATION_SECONDS
    # add rt_seconds to buffer dict and CSV fields
```

- Add `"response_time_seconds"` column to `_EVENT_FIELDS`.
- `get_hud_data()`: add `"art_seconds": round(self.art_seconds, 1)`. Keep `"art"` (ticks) for existing test compat.
- HUD renders `f"ART: {art_seconds:.1f}s"`.

---

## FR-08: ambulance.py augmentation

```python
from collections import deque
# in __init__:
self.position_history: deque[int] = deque(maxlen=STUCK_DETECTION_WINDOW)
```

---

## FR-09: simulation_engine.py wiring

In `__init__`, after TrafficModel init:

```python
from src.routing.router import Router
from src.intelligence.predictive_traffic import PredictiveTrafficEngine
from src.routing.decision_log import DecisionLog

self.decision_log = DecisionLog()
self.router = Router(graph, distance_matrix, node_index, self.traffic)
self.router.cch.preprocess()  # blocking; < 2s
self.predictive = PredictiveTrafficEngine(graph, self.traffic)
```

Pass `router=self.router, decision_log=self.decision_log` to `DispatcherBrain.__init__` (add these params).

In `_tick()`, insert after `traffic.update(...)`:

```python
self.predictive.tick(self.state.current_tick)
self.router.tick(self.state.current_tick)
```

---

## CHECKPOINTS (sequential, each is a hard gate)

| CP  | Gate condition                                                                                                   |
| --- | ---------------------------------------------------------------------------------------------------------------- |
| CP1 | `test_cch.py` PASS: CCH.query == nx.dijkstra_path length ±5% on 20 random pairs                               |
| CP2 | `test_dstar_lite.py` PASS: path repairs without restart on single edge block                                   |
| CP3 | `test_router.py` PASS: dispatch→travel→obstacle→reroute→arrive E2E                                         |
| CP4 | `test_metrics_tracker.py` PASS: `art_seconds == art * TICK_DURATION_SECONDS`                                 |
| CP5 | `test_predictive_traffic.py` PASS: RMSE at tick50 ≤ 0.7×RMSE at tick10                                       |
| CP6 | `test_constraint_dispatcher.py` PASS: all 4 gate variants (see §METRICS)                                      |
| CP7 | `test_simulation_regression.py` PASS: ART_new ≤ 0.70×ART_old on seeds [42,137,999]                           |
| CP8 | `pytest tests/ -v` exits 0, `outputs/decisions.jsonl` valid, `metrics_summary.csv` has `art_seconds` col |

---

## SUCCESS METRICS (automated, seeds=[42,137,999], 2000 ticks headless each)

| Metric                                   | Target                 | Fail                 |
| ---------------------------------------- | ---------------------- | -------------------- |
| Mean ART (seconds)                       | ≤ 70% of A\*-baseline | > 75%                |
| Mean tick CPU time                       | ≤ 70% of A\*-baseline | > 80%                |
| Reassignment hard-gate violations        | 0                      | ≥ 1                 |
| STUCK events resolved                    | 100%                   | < 100%               |
| Predictive RMSE improvement (tick10→50) | ≥ 30%                 | < 20%                |
| `art` in any public API                | seconds                | ticks found anywhere |
| Existing test suite                      | all PASS               | any FAIL             |

**Constraint gate test cases (test_constraint_dispatcher.py must cover all 4):**

1. `T_replacement=500s > 420` → DENY (assert no swap).
2. `T_A_current=500s > 420` → DENY (already failing site; assert no swap).
3. `gain=0.30 < 0.40` → DENY (assert no swap).
4. `T_replacement=300s, T_A_current=300s, gain=0.50` → APPROVE (assert swap executed).

---

## CONSTRAINTS (non-negotiable)

```
ALLOWED_IMPORTS_ROUTING = {networkx(load only), numpy, scipy, heapq, collections, math}
FORBIDDEN_IN_ROUTING    = {nx.dijkstra_path, nx.astar_path, nx.shortest_path, osrm, pyroutelib}
MAX_LINES_PER_FILE      = 300  (split if exceeded)
GLOBAL_MUTABLE_STATE    = 0    (no module-level caches)
PUBLIC_METHODS_ONLY     = per interface signatures above (no extra public methods)
TICK_LOOP_MUST_NOT_RAISE = True  (all routing paths catch exceptions, log, continue)
BACKWARD_COMPAT         = True  (astar.py, astar_traffic.py, all existing tests unchanged)
```

---

## AGENT AUDIT PROTOCOL

After each CP, append to `DECISIONS.md`:

```
## CP{N} | {timestamp}
DECISIONS: [decision]=[rationale referencing SPEC §]
DEVIATIONS: [what]=[why necessary]
TESTS: [name]=PASS|FAIL
GAPS: [item]=[reason deferred]
```

`DECISIONS.md` is mandatory. Missing entries = incomplete checkpoint.
