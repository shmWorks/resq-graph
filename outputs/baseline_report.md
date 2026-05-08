# Baseline Report — Random Fleet Placement (Sprint 8)

*Generated automatically by `src/analyze_baseline.py` on 2026-05-08 16:55 UTC*

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Runs completed | 10 |
| Total events processed | 226 |
| **Grand mean ART** | **26.34 ticks** |
| Grand std dev | 3.07 ticks |
| Min run ART | 21.72 ticks |
| Max run ART | 31.26 ticks |

---

## Per-Run Results

| Run | Seed | Events | Mean ART | Std ART | Ticks |
|-----|------|--------|----------|---------|-------|
| 0 | 42 | 18 | 21.72 | 6.51 | 500 |
| 1 | 43 | 25 | 23.04 | 8.98 | 500 |
| 2 | 44 | 22 | 26.68 | 9.47 | 500 |
| 3 | 45 | 21 | 29.71 | 12.44 | 500 |
| 4 | 46 | 19 | 22.84 | 5.20 | 500 |
| 5 | 47 | 32 | 27.50 | 10.20 | 500 |
| 6 | 48 | 27 | 31.26 | 14.39 | 500 |
| 7 | 49 | 22 | 24.14 | 6.78 | 500 |
| 8 | 50 | 17 | 28.77 | 11.03 | 500 |
| 9 | 51 | 23 | 27.70 | 13.03 | 500 |

---

## Visualizations

### ART Distribution
![ART Distribution](figures/art_distribution.png)

### ART per Run (Time-Series)
![ART Time-Series](figures/art_timeseries.png)

---

## Observations — Inefficiencies of Random Placement

1. **Spatial clustering**: Random sampling frequently places multiple stations
   in the same district, leaving other zones uncovered. This increases travel
   distance for events that spawn far from any cluster.

2. **Uncovered zones**: With only 5 stations on a large road network, random
   placement has no awareness of event demand density. High-demand areas
   identified by the HDBSCAN hotspot detector (Sprint 6) are often left without
   nearby coverage.

3. **High variance between runs**: The wide standard deviation in ART across
   runs (std = 3.07) reflects the randomness of the placement.
   Optimized placements should reduce both mean ART and variance.

4. **Long travel distances**: Without optimized positioning, ambulances
   regularly traverse longer paths, contributing to higher response times.
   The A* pathfinder correctly finds shortest routes, but start proximity
   is the dominant factor.

---

## Next Steps

- **Sprint 9**: Run the same scenario with the Genetic Algorithm–optimized
  fleet (`src/run_genetic_algorithm.py`) to obtain a comparable ART.
- Compare grand mean ART (random: **26.34**) against optimized ART
  to quantify the improvement.
- Use `outputs/random_fleet_log.json` to audit individual placement sets if
  any run shows an anomalous ART.
