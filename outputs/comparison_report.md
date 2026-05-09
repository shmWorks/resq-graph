# Fleet Comparison Report — AI vs Random Baseline (Sprint 9)

*Generated automatically by `src/analyze_comparison.py` on 2026-05-09 05:35 UTC*

---

## Summary

| Metric | Baseline (Random) | AI Optimised | Δ |
|--------|:-----------------:|:------------:|:---:|
| Grand mean ART (ticks) | 25.83 | 25.67 | +0.6% |
| Std dev across runs | 1.63 | 1.52 | — |

---

## Statistical Analysis

| Test | Value |
|------|-------|
| Paired t-statistic | 0.3421 |
| Two-tailed p-value | 0.740154 |
| Cohen's d | 0.1004 |
| Significant (α=0.05) | No ✗ |

The improvement is **not statistically significant** (p=0.7402).
A positive Cohen's d = 0.1004 indicates the AI fleet outperforms the random baseline.

---

## Visualizations

### ART Distribution
![art_distribution](figures/comparison_art_distribution.png)

### ART per Run (Time-Series)
![art_timeseries](figures/comparison_art_timeseries.png)

### Coverage Heatmap — AI Fleet
![coverage_heatmap](figures/comparison_coverage_heatmap.png)

### Station Placement Comparison
![station_placement](figures/comparison_station_placement.png)

---

## Methodology

- **Baseline**: 10 runs × 1000 ticks with random station placement
  (`src/run_baseline.py`, Sprint 8).
- **AI fleet**: Same 10 runs × 1000 ticks with GA-optimised fixed stations
  (`src/run_ai_fleet.py`, Sprint 9).
- **Seed parity**: Both experiments used identical per-run event seeds to ensure
  the event sequence is identical for each paired run.
- **Test**: Paired two-tailed Student's t-test on per-run mean ART vectors.
- **Effect size**: Cohen's d using pooled standard deviation.

---

## Conclusion

The experiment did not detect a statistically significant improvement. Review GA convergence (Sprint 3) or increase the number of simulation runs for higher statistical power.
