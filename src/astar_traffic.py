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
from __future__ import annotations

import heapq
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.traffic import TrafficModel


def _haversine(G, u: int, v: int) -> float:
    """Geodesic heuristic (same formula as the base astar.py)."""
    lat1, lon1 = float(G.nodes[u]["y"]), float(G.nodes[u]["x"])
    lat2, lon2 = float(G.nodes[v]["y"]), float(G.nodes[v]["x"])
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi   = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
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
    g_score: dict[int, float] = {node: float("inf") for node in G.nodes}
    g_score[start] = 0.0
    f_score: dict[int, float] = {node: float("inf") for node in G.nodes}
    f_score[start] = _haversine(G, start, goal)

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path: list[int] = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for neighbour in G.neighbors(current):
            cost = _edge_cost(current, neighbour)
            tentative_g = g_score[current] + cost
            if tentative_g < g_score[neighbour]:
                came_from[neighbour] = current
                g_score[neighbour]   = tentative_g
                f_score[neighbour]   = tentative_g + _haversine(G, neighbour, goal)
                heapq.heappush(open_set, (f_score[neighbour], neighbour))

    return None
