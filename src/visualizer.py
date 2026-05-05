"""
visualizer.py – Sprint 2 refactor.

Wraps PygameViewer for interactive path display while keeping the
original matplotlib-based save_path behaviour for offline use.

Public API (unchanged signature from Sprint 1)
----------------------------------------------
visualize_path(G, path, start, goal, title, save_path)
    • save_path is None  → opens PygameViewer interactively.
    • save_path is set   → renders to PNG via matplotlib (offline / CI mode).
"""

from __future__ import annotations

import os
import matplotlib
matplotlib.use("Agg")          # non-interactive – safe alongside pygame
import matplotlib.pyplot as plt


# ── Matplotlib offline renderer (CI / headless) ───────────────────────────────

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


# ── Interactive Pygame renderer ───────────────────────────────────────────────

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


# ── Unified public entry point ────────────────────────────────────────────────

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