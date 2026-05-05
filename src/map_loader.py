import osmnx as ox
import networkx as nx
import os
import json
import matplotlib
matplotlib.use("Agg")          # non-interactive backend – safe to import before pygame
import matplotlib.pyplot as plt

DATA_DIR = "data"
GRAPH_PATH = os.path.join(DATA_DIR, "model_town.graphml")
STATS_PATH = os.path.join(DATA_DIR, "model_town_stats.json")

ox.settings.use_cache = True                 # cache results for faster reruns
ox.settings.log_console = True               # show logs in console
ox.settings.overpass_max_query_area_size = 50_000_000  # increase max query area (50 km^2)

bbox = (74.347, 31.505, 74.370, 31.535)

# ── Derived output paths ──────────────────────────────────────────────────────
MAP_BG_PATH        = os.path.join(DATA_DIR, "map_bg.png")
NODE_POS_PATH      = os.path.join(DATA_DIR, "node_positions.json")

def remove_isolated_nodes(G):
    isolated = list(nx.isolates(G))
    G_clean = G.copy()
    G_clean.remove_nodes_from(isolated)
    return G_clean, len(isolated)


def get_graph_stats(G):
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "weakly_connected": nx.is_weakly_connected(G),
    }


def bake_map():
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(GRAPH_PATH):
        print("GraphML exists. Loading from disk...")
        G = nx.read_graphml(GRAPH_PATH)
        return G

    print("GraphML not found. Downloading from OSM...")

    G = ox.graph_from_bbox(
        bbox,
        simplify=True,
        network_type="drive"
    )

    print("Removing isolated nodes...")
    G_clean, removed = remove_isolated_nodes(G)

    print("Saving GraphML...")
    ox.save_graphml(G_clean, GRAPH_PATH)

    print("Saving statistics...")
    stats = get_graph_stats(G_clean)
    stats["isolated_nodes_removed"] = removed

    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=4)
    G_test = nx.read_graphml(GRAPH_PATH)
    assert G_test.number_of_nodes() > 0
    print("Reload verification successful.")

    return G_clean


# ── Sprint 1 additions ────────────────────────────────────────────────────────

def render_to_png(G, path: str = MAP_BG_PATH, dpi: int = 150) -> None:
    """Render the street network to a PNG file for use as a Pygame background.

    Parameters
    ----------
    G : networkx.Graph
        The street network (nodes must have 'x' lon and 'y' lat attributes).
    path : str
        Destination file path (default: data/map_bg.png).
    dpi : int
        Resolution of the output image.
    """
    from map_config import SCREEN_WIDTH, SCREEN_HEIGHT

    # Figure size in inches so that dpi * inches == pixel dims
    fig_w = SCREEN_WIDTH  / dpi
    fig_h = SCREEN_HEIGHT / dpi

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor("#1a1a2e")       # dark navy background
    ax.set_facecolor("#1a1a2e")

    for u, v, _ in G.edges(data=True):
        x1, y1 = float(G.nodes[u]["x"]), float(G.nodes[u]["y"])
        x2, y2 = float(G.nodes[v]["x"]), float(G.nodes[v]["y"])
        ax.plot([x1, x2], [y1, y2], color="#334155", linewidth=0.8, alpha=0.9)

    ax.axis("off")
    ax.set_xlim(bbox[0], bbox[2])
    ax.set_ylim(bbox[1], bbox[3])
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    print(f"Map background saved to: {path}")


def save_node_positions(G, path: str = NODE_POS_PATH) -> dict:
    """Compute and persist pixel positions for every graph node.

    Uses :func:`map_config.latlon_to_pixel` so the JSON is consistent with
    whatever the Pygame renderer will compute at runtime.

    Parameters
    ----------
    G : networkx.Graph
        Street network with 'x' and 'y' node attributes.
    path : str
        Destination JSON file (default: data/node_positions.json).

    Returns
    -------
    dict
        Mapping ``{node_id: [px, py]}``.
    """
    from map_config import latlon_to_pixel

    positions = {}
    for node in G.nodes:
        lat = float(G.nodes[node]["y"])
        lon = float(G.nodes[node]["x"])
        px, py = latlon_to_pixel(lat, lon, bbox)
        positions[str(node)] = [px, py]

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(positions, f)
    print(f"Node positions saved to: {path}  ({len(positions)} nodes)")
    return positions
