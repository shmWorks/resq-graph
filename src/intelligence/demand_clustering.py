"""
demand_clustering.py – Sprint 6 (US-022)

Demand Clustering Module.

Wraps the custom HDBSCAN implementation to turn a list of active accident
locations into a list of ``Hotspot`` objects, each representing a dense
demand cluster with a centroid node and pixel position.

Public API
----------
    from src.intelligence.demand_clustering import DemandClusterer, Hotspot

    clusterer = DemandClusterer(
        node_positions=node_positions,
        min_cluster_size=3,
        min_samples=2,
    )
    hotspots = clusterer.run(active_events)  # → list[Hotspot]
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from src.intelligence.hdbscan import HDBSCAN

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Hotspot:
    """A dense demand cluster detected by HDBSCAN.

    Attributes
    ----------
    cluster_id : int
        Zero-based cluster index (matches HDBSCAN label).
    centroid_node : int
        Graph node ID closest to the geometric centroid of the cluster.
    pixel_pos : tuple[int, int]
        Pixel coordinates of *centroid_node* for Pygame rendering.
    member_nodes : list[int]
        All graph node IDs belonging to this cluster.
    member_pixel_positions : list[tuple[int, int]]
        Pixel positions for each member (used for convex-hull drawing).
    size : int
        Number of events in the cluster.
    """
    cluster_id:             int
    centroid_node:          int
    pixel_pos:              tuple[int, int]
    member_nodes:           list[int]      = field(default_factory=list)
    member_pixel_positions: list[tuple[int, int]] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.member_nodes)


# ── Clusterer ─────────────────────────────────────────────────────────────────

class DemandClusterer:
    """Converts active accident locations into ``Hotspot`` objects.

    Parameters
    ----------
    node_positions : dict[int, list | tuple]
        Mapping from graph node ID → [px, py] pixel coordinates.
    min_cluster_size : int
        Passed through to HDBSCAN.
    min_samples : int
        Passed through to HDBSCAN.
    """

    def __init__(
        self,
        node_positions:   dict,
        min_cluster_size: int = 3,
        min_samples:      int = 2,
    ) -> None:
        self.node_positions   = node_positions
        self.min_cluster_size = min_cluster_size
        self.min_samples      = min_samples

    # ── Public ────────────────────────────────────────────────────────────────

    def run(self, active_events: list) -> list[Hotspot]:
        """Cluster active accidents and return a list of Hotspots.

        Parameters
        ----------
        active_events :
            Any iterable of objects with ``location`` (graph node ID) and
            ``pixel_pos`` (tuple[int, int]) attributes.

        Returns
        -------
        hotspots : list[Hotspot]
            One entry per cluster found (empty list if fewer events than
            ``min_cluster_size``).
        """
        if not active_events:
            return []

        # Build point cloud from pixel positions (float64 for HDBSCAN)
        points = np.array(
            [event.pixel_pos for event in active_events],
            dtype=np.float64,
        )
        node_ids = [event.location for event in active_events]

        # Run HDBSCAN
        hdb = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
        )
        labels = hdb.fit_predict(points)

        unique_labels = set(labels) - {-1}
        if not unique_labels:
            logger.debug("HDBSCAN: no clusters found (all points are noise).")
            return []

        hotspots: list[Hotspot] = []

        for cid in sorted(unique_labels):
            mask = labels == cid

            # Gather member info
            member_pixels = [
                (int(points[i][0]), int(points[i][1]))
                for i in range(len(points)) if mask[i]
            ]
            member_nodes = [node_ids[i] for i in range(len(node_ids)) if mask[i]]

            # Geometric centroid of pixel positions
            centroid_px = np.mean(points[mask], axis=0)

            # Nearest node to centroid
            centroid_node, centroid_pix = self._nearest_node(centroid_px)

            hs = Hotspot(
                cluster_id=int(cid),
                centroid_node=centroid_node,
                pixel_pos=centroid_pix,
                member_nodes=member_nodes,
                member_pixel_positions=member_pixels,
            )
            hotspots.append(hs)
            logger.info(
                "Hotspot %d: %d members, centroid node=%d, pixel=%s",
                cid, hs.size, centroid_node, centroid_pix,
            )

        return hotspots

    # ── Private ───────────────────────────────────────────────────────────────

    def _nearest_node(
        self, centroid_px: np.ndarray
    ) -> tuple[int, tuple[int, int]]:
        """Return the graph node whose pixel position is closest to *centroid_px*.

        Parameters
        ----------
        centroid_px : np.ndarray, shape (2,)
            Target pixel coordinate [px, py].

        Returns
        -------
        (node_id, pixel_pos) : tuple[int, tuple[int, int]]
            The best-matching node and its mapped pixel coordinates.
        """
        best_node:  int              = -1
        best_dist:  float            = float("inf")
        best_pixel: tuple[int, int]  = (0, 0)

        for node_id, pos in self.node_positions.items():
            px, py = float(pos[0]), float(pos[1])
            d = (px - centroid_px[0]) ** 2 + (py - centroid_px[1]) ** 2
            if d < best_dist:
                best_dist  = d
                best_node  = int(node_id)
                best_pixel = (int(px), int(py))

        return best_node, best_pixel
