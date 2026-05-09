# Sprint 12: Performance Optimization & Scaling

**Sprint Goal:** Optimize for larger simulations and longer runs  
**Story Points:** 16 | **Duration:** Week 12 | **Baseline:** Sprint 11 (224 tests passing)

---

## Execution Order

1. **US-045 (Profile)** → Data-driven decisions for US-046/047/048
2. **US-046 (A\*)** → Fix hottest CPU path first
3. **US-047 (Renderer)** → Reduce per-frame overhead
4. **US-048 (Scaling)** → Validate at 10,000+ ticks

---

## US-045: Profile Code & Identify Bottlenecks (3 pts)

### Current Bottlenecks (from code review)

| Issue | File | Impact |
|---|---|---|
| A* pre-allocates `g_score`/`f_score` for ALL nodes per call | `astar.py:37-39` | O(N) per call for ~2000 nodes |
| Haversine recomputed per neighbour expansion | `astar.py:4-12` | Trig on every edge relaxation |
| Full-screen redraw every tick (`REDRAW_INTERVAL=1`) | `pygame_renderer.py:161` | 1.08M pixels cleared/redrawn per frame |
| `font.render()` per ambulance per frame | `pygame_renderer.py:382` | 10 ambulances = 10 font renders/frame |
| Traffic cache invalidated every tick | `simulation_engine.py:237` | Cache rebuilt constantly |

### Tasks

#### [NEW] `scripts/profile_simulation.py`
cProfile runner: 1000-tick headless sim, dumps `outputs/profile_1000_ticks.prof` + top 30 functions by cumulative time.

#### [MODIFY] `src/rendering/pygame_renderer.py`
Add `debug_timing: bool = False` param to `draw()`. When enabled, uses `pygame.time.get_ticks()` to measure ms per render layer (bg, traffic, events, hotspots, paths, sprites, hud).

#### [NEW] `outputs/profiling_report.md`
Document: top 5 slowest functions, call graph summary, render breakdown, root cause analysis, recommended fixes mapped to US-046/047/048.

---

## US-046: Optimize A* Search Performance (5 pts)

**Target:** < 50ms per call, no correctness regression.

### Tasks

#### [MODIFY] `src/astar.py` + `src/astar_traffic.py`

**Task 1 — Lazy g_score/f_score:**
Replace `{node: float('inf') for node in G.nodes}` (O(N)) with sparse dicts + `.get(node, float('inf'))`.

**Task 2 — Closed-set pruning:**
Add `closed: set` to skip already-expanded nodes popped from the heap.

**Task 3 — Haversine cache:**
Module-level `_RAD_CACHE` dict to avoid `math.radians()` per edge relaxation.

#### [NEW] `src/astar_cache.py`
**Task 4 — LRU path cache:** Wrap `astar()` with `@lru_cache(maxsize=512)` for static (non-traffic) lookups. Traffic-aware calls bypass the cache.

#### [NEW] `scripts/benchmark_astar.py`
**Task 5 — Benchmark:** 10 random (start, goal) pairs on model_town.graphml, measure avg ms. Target < 50ms.

**Task 6 — Verification:** `pytest tests/unit/test_astar.py tests/regression/ -v` must all pass.

---

## US-047: Optimize Pygame Renderer Performance (4 pts)

**Target:** Stable 60 FPS at 1200×900 with 10 ambulances + 20 active events.

### Tasks

#### [MODIFY] `src/rendering/pygame_renderer.py`

**Task 1 — Dirty-rect rendering:**
Replace `pygame.display.flip()` with `pygame.display.update(dirty_rects)`. Background drawn once; only ambulance/event regions redrawn per frame.

**Task 2 — Sprite caching with `convert_alpha()`:**
Pre-render ambulance sprites (circle + ID label) at init. Cache per `(state, amb_id)` key. Eliminates per-frame `font.render()` + `draw.circle()`.

**Task 3 — Cache HUD & hotspot surfaces:**
HUD surface regenerated only when data changes (keyed by tick/idle_count/art). Hotspot hull surface reused when hotspot list unchanged.

#### [MODIFY] `src/simulation/simulation_engine.py`

**Task 4 — Reduce traffic cache invalidation:**
Invalidate every 5 ticks instead of every tick. Congestion changes slowly.

```python
if self.renderer and self.state.current_tick % 5 == 0:
    self.renderer.invalidate_traffic_cache()
```

#### [NEW] `scripts/benchmark_fps.py`
**Task 5 — FPS benchmark:** 500 ticks with rendering under SDL dummy, measure avg FPS. Assert >= 60.

---

## US-048: Enable Simulation Scaling (4 pts)

**Target:** 10,000+ ticks, 10+ ambulances, < 10 minutes headless, no memory leaks.

### Tasks

#### [MODIFY] `src/simulation/metrics_tracker.py`

**Task 1 — Streaming ART:**
Add `_rt_sum: float = 0.0`. Increment on each `record_response()`. Make `.art` return `_rt_sum / len(response_times)` → O(1) instead of O(N) `sum()`.

#### [MODIFY] `src/simulation/sim_logger.py`

**Task 2 — Efficient `tail()` access:**
Replace `list(self._deque)[-n:]` with indexed access to avoid full-deque copy per frame.

#### [MODIFY] `src/simulation/simulation_engine.py`

**Task 3 — Reuse position dict:**
Mutate existing `_amb_pos_cache` dict instead of creating a new dict every tick.

**Task 4 — Scaled log buffer:**
Reduce `SimLogBuffer` capacity to 50 for runs > 5000 ticks.

#### [NEW] `tests/unit/test_surface_leak.py`

**Task 5 — Surface leak test:** Run 10,000 headless ticks, verify no `MemoryError` and tick count reached target.

#### [NEW] `tests/integration/test_scaling.py`

**Task 6 — Scaling test:** 10,000 ticks + 10 ambulances, assert completes in < 600s, response_times non-empty.

---

## New Files Summary

| File | US | Purpose |
|---|---|---|
| `scripts/profile_simulation.py` | 045 | cProfile runner |
| `scripts/benchmark_astar.py` | 046 | A* timing benchmark |
| `scripts/benchmark_fps.py` | 047 | FPS benchmark |
| `src/astar_cache.py` | 046 | LRU-cached A* wrapper |
| `outputs/profiling_report.md` | 045 | Bottleneck analysis |
| `tests/unit/test_surface_leak.py` | 048 | Surface leak validation |
| `tests/integration/test_scaling.py` | 048 | 10K tick scaling test |

## Modified Files Summary

| File | US | Change |
|---|---|---|
| `src/astar.py` | 046 | Lazy init, closed-set, haversine cache |
| `src/astar_traffic.py` | 046 | Lazy init, closed-set, haversine cache |
| `src/rendering/pygame_renderer.py` | 045,047 | debug_timing, dirty-rect, sprite cache, HUD cache |
| `src/simulation/simulation_engine.py` | 047,048 | Reduced invalidation, reused dict, scaled buffer |
| `src/simulation/metrics_tracker.py` | 048 | Streaming `_rt_sum` for O(1) ART |
| `src/simulation/sim_logger.py` | 048 | Efficient `tail()` |

## Verification Plan

```bash
# 1. No regression
pytest tests/ -v

# 2. A* benchmark
python scripts/benchmark_astar.py

# 3. FPS benchmark  
python scripts/benchmark_fps.py

# 4. Scaling test
pytest tests/integration/test_scaling.py -v -s

# 5. Surface leak test
pytest tests/unit/test_surface_leak.py -v
```

## Risk Register

| Risk | Mitigation |
|---|---|
| A* cache returns stale paths when traffic changes | Cache only static calls; traffic-aware always recomputes |
| Dirty-rect rendering causes visual glitches | Fall back to full `flip()` if dirty count > threshold |
| 10K-tick test too slow for CI | Mark `@pytest.mark.slow`, skip in CI |
| `convert_alpha()` fails under SDL dummy | Wrap in try/except, fall back to unconverted surface |
