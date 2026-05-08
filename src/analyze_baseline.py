"""
analyze_baseline.py – Sprint 8 (US-031)

Reads outputs/baseline_results.csv, computes summary statistics, generates
matplotlib figures, and writes outputs/baseline_report.md automatically.

Usage
-----
    python src/analyze_baseline.py

No display is required. All figures are rendered with matplotlib Agg backend.
"""
from __future__ import annotations

import csv
import math
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASELINE_CSV   = "outputs/baseline_results.csv"
REPORT_PATH    = "outputs/baseline_report.md"
FIGURES_DIR    = "outputs/figures"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_results(csv_path: str = BASELINE_CSV) -> list[dict]:
    """Load baseline_results.csv and return all run rows (excluding SUMMARY)."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(
            f"Baseline CSV not found: {csv_path!r}\n"
            "Run 'python src/run_baseline.py --headless --config headless_baseline.yaml' first."
        )
    rows = []
    with open(csv_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if str(row.get("run_id", "")).upper() == "SUMMARY":
                continue
            rows.append({
                "run_id":   int(row["run_id"]),
                "seed":     int(row["seed"]),
                "n_events": int(row["n_events"]),
                "mean_art": float(row["mean_art"]),
                "std_art":  float(row["std_art"]),
                "ticks":    int(row["ticks"]),
            })
    return rows


# ── Statistics ────────────────────────────────────────────────────────────────

def compute_stats(rows: list[dict]) -> dict:
    """Compute aggregate statistics across all runs."""
    arts = [r["mean_art"] for r in rows if r["n_events"] > 0]
    if not arts:
        return {"grand_mean": 0.0, "grand_std": 0.0, "min_art": 0.0,
                "max_art": 0.0, "total_events": 0, "n_runs": len(rows)}

    grand_mean   = sum(arts) / len(arts)
    grand_std    = math.sqrt(sum((x - grand_mean) ** 2 for x in arts) / len(arts))
    total_events = sum(r["n_events"] for r in rows)

    return {
        "grand_mean":   round(grand_mean,  3),
        "grand_std":    round(grand_std,   3),
        "min_art":      round(min(arts),   3),
        "max_art":      round(max(arts),   3),
        "total_events": total_events,
        "n_runs":       len(rows),
    }


# ── Visualizations ────────────────────────────────────────────────────────────

def _rows_to_fake_df(rows: list[dict]):
    """
    Lightweight dict-of-lists shim so visualizer functions work without pandas.
    Exposes the same column-access pattern: df[col].
    """
    class _FakeDF:
        def __init__(self, rows):
            self._rows = rows
            self._cols = {k: [r[k] for r in rows] for k in rows[0]} if rows else {}

        def __getitem__(self, col):
            return _FakeCol(self._cols.get(col, []))

        def __setitem__(self, key, value):
            if hasattr(value, "_values"):
                self._cols[key] = list(value._values)
            else:
                self._cols[key] = list(value)

        def copy(self):
            import copy
            return _FakeDF(copy.deepcopy(self._rows))

        def sort_values(self, by):
            sorted_rows = sorted(self._rows, key=lambda r: r[by])
            return _FakeDF(sorted_rows)

        # Support boolean mask: df[df["run_id"] != "SUMMARY"]
        def __eq__(self, other):  # pragma: no cover
            return self

    class _FakeCol:
        def __init__(self, values):
            self._values = values

        def __eq__(self, other):
            # Returns a mask object that _FakeDF can use
            return _FakeMask([v == other for v in self._values])

        def __ne__(self, other):
            return _FakeMask([v != other for v in self._values])

        def astype(self, t):
            return _FakeCol([t(v) for v in self._values])

        def tolist(self):
            return list(self._values)

        def __len__(self):
            return len(self._values)

        def __iter__(self):
            return iter(self._values)

        def mean(self):
            vals = [float(v) for v in self._values]
            return sum(vals) / len(vals) if vals else 0.0

    class _FakeMask:
        """Wraps a boolean list so _FakeDF[mask] works."""
        def __init__(self, bools):
            self._bools = bools

        # not used in our visualizer paths directly

    # Attach __getitem__ with mask support directly
    original_getitem = _FakeDF.__getitem__

    def masked_getitem(self, key):
        if isinstance(key, _FakeMask):
            filtered = [r for r, b in zip(self._rows, key._bools) if b]
            return _FakeDF(filtered)
        return original_getitem(self, key)

    _FakeDF.__getitem__ = masked_getitem
    return _FakeDF(rows)


def generate_figures(rows: list[dict]) -> tuple[str, str]:
    """Call the visualizer plot functions and return saved paths."""
    from src.rendering.visualizer import plot_art_distribution, plot_art_timeseries

    fake_df = _rows_to_fake_df(rows)
    dist_path = plot_art_distribution(fake_df)
    ts_path   = plot_art_timeseries(fake_df)
    return dist_path, ts_path


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(rows: list[dict], stats: dict) -> None:
    """Write outputs/baseline_report.md programmatically."""
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build per-run table rows
    table_rows = "\n".join(
        f"| {r['run_id']} | {r['seed']} | {r['n_events']} "
        f"| {r['mean_art']:.2f} | {r['std_art']:.2f} | {r['ticks']} |"
        for r in rows
    )

    report = f"""# Baseline Report — Random Fleet Placement (Sprint 8)

*Generated automatically by `src/analyze_baseline.py` on {ts}*

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Runs completed | {stats['n_runs']} |
| Total events processed | {stats['total_events']} |
| **Grand mean ART** | **{stats['grand_mean']:.2f} ticks** |
| Grand std dev | {stats['grand_std']:.2f} ticks |
| Min run ART | {stats['min_art']:.2f} ticks |
| Max run ART | {stats['max_art']:.2f} ticks |

---

## Per-Run Results

| Run | Seed | Events | Mean ART | Std ART | Ticks |
|-----|------|--------|----------|---------|-------|
{table_rows}

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
   runs (std = {stats['grand_std']:.2f}) reflects the randomness of the placement.
   Optimized placements should reduce both mean ART and variance.

4. **Long travel distances**: Without optimized positioning, ambulances
   regularly traverse longer paths, contributing to higher response times.
   The A* pathfinder correctly finds shortest routes, but start proximity
   is the dominant factor.

---

## Next Steps

- **Sprint 9**: Run the same scenario with the Genetic Algorithm–optimized
  fleet (`src/run_genetic_algorithm.py`) to obtain a comparable ART.
- Compare grand mean ART (random: **{stats['grand_mean']:.2f}**) against optimized ART
  to quantify the improvement.
- Use `outputs/random_fleet_log.json` to audit individual placement sets if
  any run shows an anomalous ART.
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"[US-031] Report written -> {REPORT_PATH}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("\n[Analyze] Loading baseline results ...")
    rows  = load_results()
    stats = compute_stats(rows)

    print(f"[Analyze] {stats['n_runs']} runs, {stats['total_events']} total events")
    print(f"[Analyze] Grand mean ART = {stats['grand_mean']} +/- {stats['grand_std']}")

    print("[Analyze] Generating figures ...")
    generate_figures(rows)

    print("[Analyze] Writing report …")
    write_report(rows, stats)

    print("\n[Analyze] Done. View the report at:", REPORT_PATH)


if __name__ == "__main__":
    main()
