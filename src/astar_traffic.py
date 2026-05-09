"""
astar_traffic.py – Sprint 7 (US-026)

Traffic-aware A* pathfinding.

Wraps the base ``astar()`` function to use current edge weights from the
``TrafficModel`` instead of static ``length`` attributes.  When no
``TrafficModel`` is supplied the function falls back to the original
behaviour (pure length-based A*).

Public API
----------
    from src.astar_traffic import astar_traffic

    path = astar_traffic(graph, start, goal, traffic_model)
"""
import heapq
import math
from typing import TYPE_CHECKING

# Re-use the same radians cache populated by astar.py to avoid redundant trig
from src.astar import _get_radians

if TYPE_CHECKING:
    from src.simulation.traffic import TrafficModel


def _haversine(G, u: int, v: int) -> float:
    """Geodesic heuristic using shared radians cache."""
    phi1, lam1 = _get_radians(G, u)
    phi2, lam2 = _get_radians(G, v)
    R = 6_371_000
    dphi    = phi2 - phi1
    dlambda = lam2 - lam1
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def astar_traffic(
    G,
    start: int,
    goal:  int,
    traffic: "TrafficModel | None" = None,
) -> list[int] | None:
    """A* pathfinding using current traffic-weighted edge costs.

    Parameters
    ----------
    G : networkx.Graph / MultiGraph
        Road network with ``'x'`` / ``'y'`` node attributes.
    start, goal : int
        Source and target node IDs.
    traffic : TrafficModel, optional
        When provided, ``traffic.get_weight(u, v)`` replaces the static
        ``'length'`` edge attribute.  When ``None``, the function behaves
        identically to the original ``astar()``.

    Returns
    -------
    list[int] or None
        Ordered node-ID path, or ``None`` if no path exists.
    """
    if len(G.nodes) == 0:
        raise ValueError("Graph is empty.")
    if start == goal:
        return [start]
    if start not in G or goal not in G:
        return None

    def _edge_cost(u: int, v: int) -> float:
        if traffic is not None:
            return traffic.get_weight(u, v)
        # Fall back: minimum length over parallel edges (MultiGraph)
        edge_data = G[u][v]
        if isinstance(edge_data, dict) and all(isinstance(k, int) for k in edge_data):
            # MultiGraph
            return min(float(d.get("length", 1.0)) for d in edge_data.values())
        return float(edge_data.get("length", 1.0))

    open_set: list[tuple[float, int]] = []
    heapq.heappush(open_set, (0.0, start))

    came_from: dict[int, int] = {}
    # Sparse dicts: avoids O(N) pre-allocation over the entire graph
    g_score: dict[int, float] = {start: 0.0}
    closed:  set[int]         = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            path: list[int] = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        g_cur = g_score[current]
        for neighbour in G.neighbors(current):
            if neighbour in closed:
                continue
            cost = _edge_cost(current, neighbour)
            tentative_g = g_cur + cost
            if tentative_g < g_score.get(neighbour, float('inf')):
                came_from[neighbour] = current
                g_score[neighbour]   = tentative_g
                f = tentative_g + _haversine(G, neighbour, goal)
                heapq.heappush(open_set, (f, neighbour))

    return None
