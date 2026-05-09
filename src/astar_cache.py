"""
astar_cache.py – Sprint 12 (US-046)

LRU-cached A* wrapper for static (non-traffic) lookups.

Traffic-aware calls MUST bypass this cache because edge weights change
per tick. Use astar_traffic() directly when a TrafficModel is active.

Usage:
    from src.astar_cache import astar_static

    path = astar_static(graph, start, goal)
    # Returns cached result if (start, goal) was seen before on this graph.
"""
from __future__ import annotations

import functools
from typing import Optional

from src.astar import astar


# Registry maps id(graph) → graph object so the cache key can be an int
_GRAPH_REGISTRY: dict[int, object] = {}


@functools.lru_cache(maxsize=512)
def _cached_astar(graph_id: int, start, goal) -> Optional[tuple]:
    """Internal cached call. Returns a tuple (for hashability) or None."""
    graph = _GRAPH_REGISTRY.get(graph_id)
    if graph is None:
        return None
    result = astar(graph, start, goal)
    return tuple(result) if result is not None else None


def astar_static(graph, start, goal) -> Optional[list]:
    """
    LRU-cached A* for graphs whose edge weights never change.

    Parameters
    ----------
    graph : networkx.MultiGraph
        The road network. Must be the same object (by identity) across calls
        for the cache to be effective.
    start, goal : node IDs

    Returns
    -------
    list[node] or None
        Cached path if available; freshly computed otherwise.
    """
    gid = id(graph)
    _GRAPH_REGISTRY[gid] = graph       # keep a strong reference
    result = _cached_astar(gid, start, goal)
    return list(result) if result is not None else None


def clear_cache() -> None:
    """Flush the LRU cache and graph registry (useful between test runs)."""
    _cached_astar.cache_clear()
    _GRAPH_REGISTRY.clear()
