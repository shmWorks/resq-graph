"""
bake_map.py – Sprint 1 one-time setup script.

Run this ONCE (or whenever the graph changes) to produce:
    data/map_bg.png          – dark street-network background for Pygame
    data/node_positions.json – {node_id: [px, py]} lookup table

Usage:
    cd src
    python bake_map.py
"""

import sys
import os

# Allow running from either the repo root or src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from map_loader import bake_map, render_to_png, save_node_positions

def main():
    print("=== bake_map: Sprint 1 setup ===\n")

    print("Step 1/3: Loading / downloading graph...")
    G = bake_map()
    print(f"  Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    print("Step 2/3: Rendering map background PNG...")
    render_to_png(G)

    print("\nStep 3/3: Writing node pixel positions...")
    positions = save_node_positions(G)

    print(f"\nDone - {len(positions)} nodes mapped.")
    print("  You can now run the Pygame visualiser.\n")


if __name__ == "__main__":
    main()
