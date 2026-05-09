"""
visualizer.py – Sprint 2 refactor + Sprint 8 baseline plots (US-031)

Moved from src/visualizer.py to src/rendering/visualizer.py for
architectural consistency. All existing public API is preserved.

Sprint 8 additions
------------------
- plot_art_distribution(results_df) → outputs/figures/art_distribution.png
- plot_art_timeseries(results_df)   → outputs/figures/art_timeseries.png

Both functions use the Agg (non-interactive) backend and require no display.
"""

from __future__ import annotations

import os
import matplotlib
matplotlib.use("Agg")          # non-interactive – safe alongside pygame
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ── Sprint 2: Matplotlib offline renderer (CI / headless) ────────────────────

def _save_matplotlib(G, path, start, goal, title: str, save_path: str) -> None:
    """Render to PNG using matplotlib (original Sprint-1 implementation)."""
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    # All edges – dark streets
    for u, v, _ in G.edges(data=True):
        x1, y1 = float(G.nodes[u]["x"]), float(G.nodes[u]["y"])
        x2, y2 = float(G.nodes[v]["x"]), float(G.nodes[v]["y"])
        ax.plot([x1, x2], [y1, y2], color="#334155", linewidth=0.5, zorder=1)

    # Highlighted path
    if path:
        xs, ys = [], []
        for a, b in zip(path[:-1], path[1:]):
            x1, y1 = float(G.nodes[a]["x"]), float(G.nodes[a]["y"])
            x2, y2 = float(G.nodes[b]["x"]), float(G.nodes[b]["y"])
            xs += [x1, x2, None]
            ys += [y1, y2, None]
        ax.plot(xs, ys, color="#38bdf8", linewidth=2.5, zorder=2)

    # Start / goal markers
    ax.scatter(float(G.nodes[start]["x"]), float(G.nodes[start]["y"]),
               c="#22c55e", s=140, zorder=5, label="Start")
    ax.scatter(float(G.nodes[goal]["x"]),  float(G.nodes[goal]["y"]),
               c="#ef4444", s=140, zorder=5, label="Goal")

    ax.legend(loc="upper left", facecolor="#0f172a", labelcolor="white")
    ax.set_title(title, fontsize=14, color="white")
    ax.set_xlabel("Longitude", color="#94a3b8")
    ax.set_ylabel("Latitude",  color="#94a3b8")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    plt.tight_layout()

    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved to: {save_path}")


# ── Sprint 2: Interactive Pygame renderer ─────────────────────────────────────

def _show_pygame(G, path, start, goal, title: str) -> None:
    """Display the path interactively via PygameViewer."""
    from draw_path import PygameViewer, load_node_positions
    from map_loader import bbox
    from map_config import latlon_to_pixel

    node_positions = load_node_positions()

    # Fall back to computing positions on the fly if JSON is absent
    if not node_positions:
        node_positions = {
            str(n): list(latlon_to_pixel(
                float(G.nodes[n]["y"]), float(G.nodes[n]["x"]), bbox
            ))
            for n in G.nodes
        }

    viewer = PygameViewer(node_positions=node_positions, title=title)
    if path:
        viewer.add_path(
            node_list=path,
            color=(56, 189, 248),   # sky-blue
            label=title,
        )

    viewer.run()


# ── Sprint 2: Unified public entry point ──────────────────────────────────────

def visualize_path(
    G,
    path,
    start,
    goal,
    title: str = "A* Path",
    save_path: str | None = None,
) -> None:
    """Visualise an A* path on the Model Town street network.

    Parameters
    ----------
    G : networkx.Graph
        Street network (nodes must have 'x' lon / 'y' lat attributes).
    path : list
        Ordered list of node IDs from *start* to *goal*.
    start : str | int
        Start node ID.
    goal : str | int
        Goal node ID.
    title : str
        Window / figure title.
    save_path : str, optional
        If given, save a static PNG (offline/CI mode).
        If ``None``, open an interactive Pygame window.
    """
    if save_path:
        _save_matplotlib(G, path, start, goal, title, save_path)
    else:
        _show_pygame(G, path, start, goal, title)


# ── Sprint 8: Baseline analysis plots (US-031) ────────────────────────────────

_FIGURES_DIR = "outputs/figures"

_DARK_BG  = "#0f172a"
_PANEL_BG = "#1e293b"
_ACCENT   = "#38bdf8"
_ACCENT2  = "#818cf8"
_TEXT     = "#e2e8f0"
_MUTED    = "#64748b"


def _apply_dark_style(fig, ax) -> None:
    """Apply a consistent dark theme to a figure/axes pair."""
    fig.patch.set_facecolor(_DARK_BG)
    ax.set_facecolor(_PANEL_BG)
    ax.tick_params(colors=_TEXT, labelsize=9)
    ax.xaxis.label.set_color(_TEXT)
    ax.yaxis.label.set_color(_TEXT)
    ax.title.set_color(_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(_MUTED)


def plot_art_distribution(results_df) -> str:
    """Plot a histogram of mean ART across all baseline runs.

    Parameters
    ----------
    results_df : pandas.DataFrame
        Must contain columns ``run_id`` (str) and ``mean_art`` (float).
        Summary rows (run_id == 'SUMMARY') are automatically excluded.

    Returns
    -------
    str
        Absolute path to the saved PNG.
    """
    import numpy as np

    data = results_df[results_df["run_id"] != "SUMMARY"]["mean_art"].astype(float)

    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_dark_style(fig, ax)

    n_bins = min(10, max(3, len(data) // 2))
    ax.hist(data, bins=n_bins, color=_ACCENT, edgecolor=_DARK_BG, alpha=0.85, zorder=2)

    mean_val = float(data.mean())
    ax.axvline(mean_val, color="#f472b6", linewidth=1.8, linestyle="--",
               label=f"Mean ART = {mean_val:.1f} ticks", zorder=3)

    ax.set_xlabel("Average Response Time (ticks)", fontsize=11)
    ax.set_ylabel("Number of Runs", fontsize=11)
    ax.set_title("Baseline ART Distribution — Random Fleet Placement", fontsize=13, pad=12)
    ax.legend(facecolor=_PANEL_BG, labelcolor=_TEXT, framealpha=0.9, fontsize=9)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.grid(axis="y", color=_MUTED, alpha=0.3, linewidth=0.7)

    plt.tight_layout()
    os.makedirs(_FIGURES_DIR, exist_ok=True)
    out = os.path.join(_FIGURES_DIR, "art_distribution.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [US-031] Saved ART distribution -> {out}")
    return out


def plot_art_timeseries(results_df) -> str:
    """Plot per-run mean ART as an overlaid time-series / bar chart.

    Parameters
    ----------
    results_df : pandas.DataFrame
        Must contain columns ``run_id``, ``mean_art``, and ``std_art``.
        Summary rows (run_id == 'SUMMARY') are automatically excluded.

    Returns
    -------
    str
        Absolute path to the saved PNG.
    """
    df = results_df[results_df["run_id"] != "SUMMARY"].copy()
    df["run_id"]   = df["run_id"].astype(int)
    df["mean_art"] = df["mean_art"].astype(float)
    df["std_art"]  = df["std_art"].astype(float)
    df = df.sort_values("run_id")

    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_dark_style(fig, ax)

    xs     = df["run_id"].tolist()
    arts   = df["mean_art"].tolist()
    stds   = df["std_art"].tolist()

    ax.bar(xs, arts, color=_ACCENT2, alpha=0.6, zorder=2, label="Mean ART per run")
    ax.errorbar(xs, arts, yerr=stds, fmt="o-", color=_ACCENT,
                linewidth=1.8, markersize=6, capsize=4, zorder=3, label="± Std Dev")

    grand_mean = float(df["mean_art"].mean())
    ax.axhline(grand_mean, color="#f472b6", linewidth=1.5, linestyle="--",
               label=f"Grand mean = {grand_mean:.1f}", zorder=4)

    ax.set_xlabel("Run ID", fontsize=11)
    ax.set_ylabel("Average Response Time (ticks)", fontsize=11)
    ax.set_title("ART per Run — Random Fleet Baseline", fontsize=13, pad=12)
    ax.legend(facecolor=_PANEL_BG, labelcolor=_TEXT, framealpha=0.9, fontsize=9)
    ax.set_xticks(xs)
    ax.grid(axis="y", color=_MUTED, alpha=0.3, linewidth=0.7)

    plt.tight_layout()
    os.makedirs(_FIGURES_DIR, exist_ok=True)
    out = os.path.join(_FIGURES_DIR, "art_timeseries.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [US-031] Saved ART time-series -> {out}")
    return out


def plot_sensitivity_lambda(df, out_path: str):
    import numpy as np
    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_dark_style(fig, ax)

    bas = df[df["fleet_type"] == "baseline"]
    ai = df[df["fleet_type"] == "ai"]

    ax.plot(bas["lambda"], bas["mean_art"], "o-", color=_ACCENT2, label="Baseline (Random)")
    ax.fill_between(bas["lambda"], bas["mean_art"] - bas["std_art"], bas["mean_art"] + bas["std_art"], color=_ACCENT2, alpha=0.2)

    ax.plot(ai["lambda"], ai["mean_art"], "s-", color=_ACCENT, label="AI (Optimised)")
    ax.fill_between(ai["lambda"], ai["mean_art"] - ai["std_art"], ai["mean_art"] + ai["std_art"], color=_ACCENT, alpha=0.2)

    ax.set_xlabel("Event Rate (λ)")
    ax.set_ylabel("Mean ART (ticks)")
    ax.set_title("Sensitivity: ART vs Event Rate (Lambda)")
    ax.legend()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity_fleet(df, out_path: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_dark_style(fig, ax)

    bas = df[df["fleet_type"] == "baseline"]
    ai = df[df["fleet_type"] == "ai"]

    ax.errorbar(bas["num_ambulances"], bas["mean_art"], yerr=bas["std_art"], fmt="o-", color=_ACCENT2, label="Baseline")
    ax.errorbar(ai["num_ambulances"], ai["mean_art"], yerr=ai["std_art"], fmt="s-", color=_ACCENT, label="AI Fleet")

    ax.set_xlabel("Number of Ambulances")
    ax.set_ylabel("Mean ART (ticks)")
    ax.set_title("Sensitivity: ART vs Fleet Size")
    ax.legend()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity_hdbscan_art(df, out_path: str):
    # Heatmap style 
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    intervals = df["rebalance_interval"].unique()

    for i, interval in enumerate(intervals):
        ax = axes[i]
        subset = df[df["rebalance_interval"] == interval]
        if subset.empty: continue
        pivot = subset.pivot(index="min_cluster_size", columns="min_samples", values="mean_art")
        im = ax.imshow(pivot.values, cmap="viridis_r", aspect="auto")
        ax.set_title(f"Interval = {interval}")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns)
        if i == 0:
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_ylabel("min_cluster_size")
        ax.set_xlabel("min_samples")
    
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Mean ART")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity_hdbscan_churn(df, out_path: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    _apply_dark_style(fig, ax)

    sc = ax.scatter(df["mean_rebalance_count"], df["mean_art"], c=df["rebalance_interval"], cmap="cool", s=100, alpha=0.8)
    fig.colorbar(sc, label="Rebalance Interval")
    
    ax.set_xlabel("Mean Rebalance Count (Churn proxy)")
    ax.set_ylabel("Mean ART (ticks)")
    ax.set_title("Trade-off: ART vs Rebalance Churn")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
