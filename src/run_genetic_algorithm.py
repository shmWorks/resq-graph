"""Run genetic algorithm for facility location optimization.

Sprint 3: Matplotlib convergence plot is retained (offline analysis).
          Station visualisation is replaced with PygameViewer + interactive
          Voronoi overlays and keyboard toggles.

Entry point: python run_genetic_algorithm.py
Keyboard shortcuts (inside the Pygame window):
    V  – toggle Voronoi coverage zones
    C  – toggle Random vs. Optimal comparison markers
    S  – save screenshot to outputs/
    ESC / close window – quit
"""
from __future__ import annotations

import json
import time
import os
import math

import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")          # non-interactive – safe alongside pygame
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi, voronoi_plot_2d

from genetic_algorithm import GeneticAlgorithm, run_genetic_algorithm
from fitness import load_fitness_function, create_node_index, compute_reachable_mask

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_graph_and_matrix():
    """Load graph and distance matrix."""
    G = nx.read_graphml("data/model_town.graphml")

    for node in G.nodes:
        G.nodes[node]["x"] = float(G.nodes[node]["x"])
        G.nodes[node]["y"] = float(G.nodes[node]["y"])

    distance_matrix = np.load("data/distance_matrix.npy")
    nodes = list(G.nodes())
    return G, distance_matrix, nodes


# ─────────────────────────────────────────────────────────────────────────────
# Convergence plot (kept as Matplotlib – offline analysis)
# ─────────────────────────────────────────────────────────────────────────────

def plot_convergence(fitness_history, save_path=None):
    """Plot convergence: generation vs best fitness."""
    plt.figure(figsize=(10, 6))
    plt.style.use("dark_background")
    plt.plot(fitness_history, color="#38bdf8", linewidth=2)
    plt.fill_between(range(len(fitness_history)), fitness_history, alpha=0.15, color="#38bdf8")
    plt.xlabel("Generation", color="#94a3b8")
    plt.ylabel("Best Fitness", color="#94a3b8")
    plt.title("GA Convergence: Best Fitness per Generation", color="white", fontsize=14)
    plt.grid(True, alpha=0.2, color="#334155")

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        print(f"Convergence plot saved to {save_path}")
    plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 3: Pygame-based station visualiser
# ─────────────────────────────────────────────────────────────────────────────

# ── Colour constants ─────────────────────────────────────────────────────────
_OPTIMAL_COL  = (56, 189, 248)   # #38bdf8 sky-blue  – optimal station
_RANDOM_COL   = (148, 163, 184)  # #94a3b8 slate     – random baseline
_VORONOI_COLS = [                # cycling palette for Voronoi regions
    (56,  189, 248,  45),
    (168, 85,  247,  45),
    (34,  197,  94,  45),
    (251, 146,  60,  45),
    (244,  63,  94,  45),
]
_STAR_RADIUS   = 10
_DOT_RADIUS    = 7


def _draw_star(surface, colour, cx, cy, r):
    """Draw a 5-pointed star centred at (cx, cy) with outer radius r."""
    import pygame
    points = []
    for i in range(10):
        angle = math.radians(-90 + i * 36)
        radius = r if i % 2 == 0 else r * 0.45
        points.append((cx + radius * math.cos(angle),
                        cy + radius * math.sin(angle)))
    pygame.draw.polygon(surface, colour, points)


def _build_voronoi_overlay(
    G,
    optimal_nodes: list,
    node_positions: dict,
    viewer_zoom: float,
    screen_w: int,
    screen_h: int,
) -> "pygame.Surface":
    """Return an RGBA Surface with translucent Voronoi polygons."""
    import pygame
    from map_config import SCREEN_WIDTH, SCREEN_HEIGHT

    w = int(SCREEN_WIDTH  * viewer_zoom)
    h = int(SCREEN_HEIGHT * viewer_zoom)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # Seed points (optimal station pixel positions at current zoom)
    seeds = []
    for n in optimal_nodes:
        pos = node_positions.get(str(n))
        if pos:
            seeds.append((pos[0] * viewer_zoom, pos[1] * viewer_zoom))

    if len(seeds) < 2:
        return surf

    # Add far-away boundary points so scipy's Voronoi covers the whole canvas
    margin = max(w, h) * 3
    boundary = [
        (-margin, -margin), (w / 2, -margin), (w + margin, -margin),
        (-margin, h / 2),                      (w + margin, h / 2),
        (-margin, h + margin), (w / 2, h + margin), (w + margin, h + margin),
    ]
    all_pts = seeds + boundary
    vor = Voronoi(all_pts)

    # Draw each finite Voronoi region
    for idx, region_idx in enumerate(vor.point_region[: len(seeds)]):
        region = vor.regions[region_idx]
        if -1 in region or len(region) == 0:
            continue
        verts = [vor.vertices[i] for i in region]
        colour = _VORONOI_COLS[idx % len(_VORONOI_COLS)]
        pygame.draw.polygon(surf, colour, verts)

    return surf


def visualize_stations_pygame(
    G,
    optimal_nodes: list,
    node_positions: dict,
) -> None:
    """Open an interactive Pygame window showing the GA station results.

    Keyboard toggles:
        V – Voronoi coverage zones
        C – Random-vs-optimal comparison
        S – screenshot
        ESC – quit
    """
    import pygame
    from draw_path import PygameViewer
    from map_config import SCREEN_WIDTH, SCREEN_HEIGHT

    # Random baseline for comparison (seeded for reproducibility)
    nodes_list = list(G.nodes())
    np.random.seed(42)
    random_nodes = list(np.random.choice(nodes_list, 5, replace=False))

    viewer = PygameViewer(node_positions=node_positions,
                          title="ResQ-Graph – Optimal Ambulance Stations")

    # ── Overlay callback ──────────────────────────────────────────────────────
    def draw_overlay(world_surf: "pygame.Surface", v: PygameViewer) -> None:
        zoom = v._zoom

        # 1. Voronoi coverage zones (toggled with V)
        if v.show_coverage:
            voronoi_surf = _build_voronoi_overlay(
                G, optimal_nodes, node_positions, zoom,
                world_surf.get_width(), world_surf.get_height()
            )
            world_surf.blit(voronoi_surf, (0, 0))

        # 2. Random station markers (toggled with C)
        if v.show_comparison:
            for n in random_nodes:
                pos = node_positions.get(str(n))
                if pos:
                    px, py = int(pos[0] * zoom), int(pos[1] * zoom)
                    pygame.draw.circle(world_surf, _RANDOM_COL, (px, py), _DOT_RADIUS)

        # 3. Optimal station markers (always visible – stars)
        for n in optimal_nodes:
            pos = node_positions.get(str(n))
            if pos:
                px, py = int(pos[0] * zoom), int(pos[1] * zoom)
                _draw_star(world_surf, _OPTIMAL_COL, px, py, _STAR_RADIUS)

    viewer.add_overlay_callback(draw_overlay)
    viewer.run()


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Matplotlib fallback (for headless / save_path usage)
# ─────────────────────────────────────────────────────────────────────────────

def visualize_stations(G, optimal_nodes, save_path=None):
    """Visualize optimal stations on map (static PNG, kept for CI)."""
    pos = {n: (G.nodes[n]["x"], G.nodes[n]["y"]) for n in G.nodes()}

    nodes_list = list(G.nodes())
    np.random.seed(42)
    random_nodes = list(np.random.choice(nodes_list, 5, replace=False))

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#334155", width=0.5, alpha=0.7)

    random_x = [pos[n][0] for n in random_nodes]
    random_y = [pos[n][1] for n in random_nodes]
    ax.scatter(random_x, random_y, c="#94a3b8", s=150, marker="o",
               label="Random Placement", zorder=3, alpha=0.7)

    optimal_x = [pos[n][0] for n in optimal_nodes]
    optimal_y = [pos[n][1] for n in optimal_nodes]
    ax.scatter(optimal_x, optimal_y, c="#38bdf8", s=400, marker="*",
               label="Optimal (GA)", zorder=4, edgecolors="white", linewidths=1)

    ax.legend(loc="upper right", fontsize=10,
              facecolor="#0f172a", labelcolor="white")
    ax.set_title("Optimal Ambulance Base Stations", color="white")
    ax.axis("off")

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        print(f"Station visualization saved to {save_path}")
    plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run full GA pipeline then open the interactive Pygame viewer."""
    print("Loading data...")
    G, distance_matrix, nodes = load_graph_and_matrix()

    print(f"Graph: {len(nodes)} nodes, {G.number_of_edges()} edges")
    print(f"Distance matrix: {distance_matrix.shape}")

    reachable_mask = compute_reachable_mask(distance_matrix)
    print(f"Reachable nodes: {reachable_mask.sum()}/{len(nodes)}")

    print("\nInitializing fitness function...")
    fitness_fn = load_fitness_function(nodes=nodes)

    ga = GeneticAlgorithm(nodes)
    print(f"\nRunning GA (Pop: {ga.pop_size}, Mutation: {ga.mutation_rate})...")
    start_time = time.time()

    best_genome = ga.run(fitness_fn, generations=100, verbose=True)

    elapsed = time.time() - start_time
    print(f"\nExecution time: {elapsed:.2f}s")

    # ── Export results ─────────────────────────────────────────────────────────
    print("\nExporting results...")
    result = {
        "optimal_stations":         best_genome,
        "best_fitness":             ga.fitness_history[-1],
        "generations":              100,
        "execution_time_seconds":   elapsed,
    }
    json_path = os.path.join(OUTPUT_DIR, "optimal_stations.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to {json_path}")

    # Convergence plot (Matplotlib, saved to disk)
    conv_path = os.path.join(OUTPUT_DIR, "convergence_plot.png")
    plot_convergence(ga.fitness_history, save_path=conv_path)

    # Static station PNG (CI / headless fallback)
    viz_path = os.path.join(OUTPUT_DIR, "optimal_stations.png")
    visualize_stations(G, best_genome, save_path=viz_path)

    print(f"\nBest genome: {best_genome}")
    print(f"Best fitness: {ga.fitness_history[-1]:.2f}")

    # ── Interactive Pygame viewer (Sprint 3) ───────────────────────────────────
    from draw_path import load_node_positions
    from map_config import latlon_to_pixel
    from map_loader import bbox

    node_positions = load_node_positions()
    if not node_positions:
        # Compute on the fly if bake_map hasn't been run yet
        node_positions = {
            str(n): list(latlon_to_pixel(
                float(G.nodes[n]["y"]), float(G.nodes[n]["x"]), bbox
            ))
            for n in G.nodes
        }

    print("\nOpening interactive Pygame viewer (V=coverage, C=compare, S=screenshot, ESC=quit)…")
    visualize_stations_pygame(G, best_genome, node_positions)

    return best_genome, ga.fitness_history


if __name__ == "__main__":
    main()