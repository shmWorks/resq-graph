"""
traffic.py – Sprint 7 (US-025)

Traffic Congestion Simulation.

Models time-varying edge weights on the road graph.  Congestion builds
up near active accident locations and decays linearly toward 1.0 (free
flow) on every tick.

Design decisions
----------------
- We store a multiplier per *undirected* edge as a ``dict[frozenset, float]``
  so that the data structure is independent of the graph's directedness.
- The ``get_weight(u, v)`` helper is used by A* and the re-routing check to
  obtain the *current* travel cost of an edge.
- The renderer reads ``edge_multipliers`` directly to colour roads
  Green → Yellow → Red.

Public API
----------
    from src.simulation.traffic import TrafficModel

    traffic = TrafficModel(graph, max_multiplier=2.5, decay_rate=0.02)
    traffic.update(active_events, current_tick)      # call once per tick
    w = traffic.get_weight(u, v)                     # current edge cost
    m = traffic.get_multiplier(u, v)                 # raw multiplier [1.0, 2.5]
"""
from __future__ import annotations

import logging
import math
from typing import Hashable

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


class TrafficModel:
    """Dynamic edge-weight model based on proximity to accidents.

    Parameters
    ----------
    graph : networkx.Graph (or MultiGraph)
        The road network.  Edge attribute ``'length'`` is used as the base
        travel cost (falls back to 1.0 if absent).
    max_multiplier : float
        Maximum congestion multiplier (plan specifies 2.5).
    decay_rate : float
        Amount subtracted from each multiplier per tick (towards 1.0).
    influence_radius : float
        Pixel distance within which an accident raises congestion on its
        adjacent edges.  Default matches roughly one city block.
    """

    def __init__(
        self,
        graph,
        node_positions:   dict,
        max_multiplier:   float = 2.5,
        decay_rate:       float = 0.02,
        influence_radius: float = 120.0,
    ) -> None:
        self.graph            = graph
        self.node_positions   = node_positions
        self.max_multiplier   = max_multiplier
        self.decay_rate       = decay_rate
        self.influence_radius = influence_radius

        # edge key → current multiplier (1.0 = free flow)
        self._multipliers: dict[frozenset, float] = {
            frozenset({u, v}): 1.0
            for u, v in graph.edges()
        }

        # Pre-compute base weights for each edge
        self._base_weights: dict[frozenset, float] = self._compute_base_weights()

    # ── Public ────────────────────────────────────────────────────────────────

    def update(self, active_events: list, current_tick: int) -> None:
        """Update all edge multipliers for this tick.

        Steps
        -----
        1. Decay all existing multipliers toward 1.0.
        2. For each active event, increase the multiplier on nearby edges.

        Parameters
        ----------
        active_events :
            Iterable of objects with ``pixel_pos : tuple[int, int]``.
        current_tick :
            Current simulation tick (used for logging only).
        """
        # Step 1: decay
        for key in self._multipliers:
            self._multipliers[key] = max(
                1.0,
                self._multipliers[key] - self.decay_rate,
            )

        # Step 2: increase near active events
        for event in active_events:
            epx, epy = float(event.pixel_pos[0]), float(event.pixel_pos[1])
            self._apply_congestion(epx, epy)

    def get_weight(self, u: int, v: int) -> float:
        """Return the current travel cost of edge (u, v).

        Cost = base_length × congestion_multiplier.
        """
        key = frozenset({u, v})
        base = self._base_weights.get(key, 1.0)
        mult = self._multipliers.get(key, 1.0)
        return base * mult

    def get_multiplier(self, u: int, v: int) -> float:
        """Return the raw multiplier for edge (u, v)  ∈ [1.0, max_multiplier]."""
        return self._multipliers.get(frozenset({u, v}), 1.0)

    def path_weight(self, path: list[int]) -> float:
        """Return the total current weight of a node-ID path."""
        if len(path) < 2:
            return 0.0
        return sum(self.get_weight(path[i], path[i + 1]) for i in range(len(path) - 1))

    @property
    def edge_multipliers(self) -> dict[frozenset, float]:
        """Read-only view of the multiplier dict (used by the renderer)."""
        return self._multipliers

    # ── Private ───────────────────────────────────────────────────────────────

    def _compute_base_weights(self) -> dict[frozenset, float]:
        """Extract ``length`` attribute for every edge."""
        weights: dict[frozenset, float] = {}
        for u, v, data in self.graph.edges(data=True):
            key = frozenset({u, v})
            if key not in weights:
                # MultiGraph: take the minimum length over parallel edges
                if isinstance(data, dict):
                    length = float(data.get("length", 1.0))
                else:
                    length = 1.0
                weights[key] = length
        return weights

    def _apply_congestion(self, epx: float, epy: float) -> None:
        """Increase multipliers on edges whose endpoints are within
        ``influence_radius`` of the accident pixel position.
        """
        for u, v in self.graph.edges():
            key = frozenset({u, v})
            pos_u = self.node_positions.get(u)
            pos_v = self.node_positions.get(v)
            if pos_u is None or pos_v is None:
                continue

            # Midpoint of the edge
            mx = (float(pos_u[0]) + float(pos_v[0])) / 2.0
            my = (float(pos_u[1]) + float(pos_v[1])) / 2.0
            dist = math.hypot(mx - epx, my - epy)

            if dist < self.influence_radius:
                # Increase proportional to proximity
                boost = (1.0 - dist / self.influence_radius) * 0.5
                self._multipliers[key] = min(
                    self.max_multiplier,
                    self._multipliers.get(key, 1.0) + boost,
                )
