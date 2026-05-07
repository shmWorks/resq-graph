"""
dispatcher.py – Sprint 6 & 7 (US-017, US-023, US-026)

DispatcherBrain: centralised coordinator that owns the active event queue,
makes ambulance-to-event assignments, tracks on-scene timers, triggers
periodic fleet rebalancing via HDBSCAN hotspots, and performs congestion-
triggered re-routing for in-transit ambulances.

Sprint 6 changes
----------------
- ``rebalance_fleet()`` now runs HDBSCAN via DemandClusterer and sends
  IDLE ambulances toward hotspot centroids in REBALANCING state.

Sprint 7 changes
----------------
- ``assign_task()`` uses traffic-aware A* (astar_traffic) and records the
  initial path weight for re-routing baseline.
- ``_check_rerouting()`` is called every tick for IN_TRANSIT ambulances;
  triggers re-route if remaining path weight has increased by ≥ 20%.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import math

from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident
from src.simulation.assignment import assign_nearest_idle
from src.simulation.metrics_tracker import MetricsTracker
from src.astar import astar
from src.astar_traffic import astar_traffic
from src.config import REBALANCE_INTERVAL, SCENE_SERVICE_TICKS
from src.intelligence.demand_clustering import DemandClusterer, Hotspot

logger = logging.getLogger(__name__)

# Sprint 7 re-routing constants (fall back to config if not in cfg dict)
_DEFAULT_REROUTE_CHECK_INTERVAL = 10   # ticks between checks per ambulance
_DEFAULT_REROUTE_THRESHOLD      = 0.20  # ≥20 % increase triggers re-route


class DispatcherBrain:
    """Central dispatch coordinator for the ResQ-Graph simulation.

    Owns three concerns:
    1. Maintaining an up-to-date view of unassigned events and idle ambulances.
    2. Making and recording assignment decisions (nearest-idle with A* path).
    3. Tracking on-scene service timers and triggering periodic rebalancing.

    The simulation loop calls ``dispatcher.tick(new_events, current_tick)``
    once per tick; no other component touches the active-events list directly.
    """

    def __init__(
        self,
        ambulances:      list[Ambulance],
        distance_matrix: np.ndarray,
        node_index:      dict,
        node_positions:  dict,
        graph,
        traffic         = None,   # TrafficModel | None  (Sprint 7)
        cfg:            dict = None,  # runtime config dict (Sprint 7)
    ):
        self.ambulances      = ambulances
        self.distance_matrix = distance_matrix
        self.node_index      = node_index
        self.node_positions  = node_positions
        self.graph           = graph
        self.traffic         = traffic        # may be None
        self._cfg            = cfg or {}

        self.active_events:   list[Accident]  = []
        self.assigned_events: dict[int, int]  = {}   # event_id → ambulance_id
        self.metrics_tracker                  = MetricsTracker()

        self._ticks_since_rebalance = 0
        # ambulance_id → tick the ambulance entered ON_SCENE
        self._on_scene_since: dict[int, int] = {}

        # Sprint 6: demand clusterer
        hdbscan_min_cs  = self._cfg.get("HDBSCAN_MIN_CLUSTER_SIZE", 3)
        hdbscan_min_smp = self._cfg.get("HDBSCAN_MIN_SAMPLES", 2)
        self._clusterer = DemandClusterer(
            node_positions   = node_positions,
            min_cluster_size = hdbscan_min_cs,
            min_samples      = hdbscan_min_smp,
        )
        # Public: renderer reads this to draw hotspot overlays
        self.hotspots: list[Hotspot] = []

        # Sprint 7 re-routing params
        self._reroute_check_interval = int(
            self._cfg.get("REROUTE_CHECK_INTERVAL", _DEFAULT_REROUTE_CHECK_INTERVAL)
        )
        self._reroute_threshold = float(
            self._cfg.get("REROUTE_THRESHOLD", _DEFAULT_REROUTE_THRESHOLD)
        )

    # ── Main tick entry point ──────────────────────────────────────────────────

    def tick(self, new_events: list[Accident], current_tick: int) -> None:
        """Called once per simulation tick by the engine.

        Order of operations
        -------------------
        1. Ingest new events.
        2. Check on-scene ambulances; complete if service time has elapsed.
        3. Check re-routing for in-transit ambulances (Sprint 7).
        4. Assign nearest idle ambulance to each unassigned event.
        5. Increment rebalance counter; call rebalance_fleet() on schedule.
        6. Snapshot metrics.
        """
        # 1. Add new events to the active queue (filtering unreachable ones)
        for event in new_events:
            reachable = False
            for amb in self.ambulances:
                try:
                    i = self.node_index[amb.current_location]
                    j = self.node_index[event.location]
                    if not math.isinf(float(self.distance_matrix[i][j])):
                        reachable = True
                        break
                except KeyError:
                    reachable = True
                    break

            if reachable:
                self.active_events.append(event)
            else:
                event.assigned_ambulance_id = -1
                logger.debug("Event %d is completely unreachable by fleet.", event.id)

        # 2. Check on-scene ambulances
        for amb in self.ambulances:
            if amb.state == AmbulanceState.ON_SCENE:
                if amb.id not in self._on_scene_since:
                    self._on_scene_since[amb.id] = current_tick
                elif current_tick - self._on_scene_since[amb.id] >= SCENE_SERVICE_TICKS:
                    self.complete_event(amb, current_tick)

        # 3. Congestion re-routing (Sprint 7)
        if self.traffic is not None:
            self._check_rerouting(current_tick)

        # 4. Assign idle ambulances to unassigned events
        for event in self.get_unassigned_events():
            idle = self.get_idle_ambulances()
            if not idle:
                break
            best = assign_nearest_idle(
                event, idle, self.distance_matrix, self.node_index
            )
            if best is not None:
                self.assign_task(best, event, current_tick)

        # 5. Periodic rebalancing
        self._ticks_since_rebalance += 1
        if self._ticks_since_rebalance >= REBALANCE_INTERVAL:
            self.rebalance_fleet(current_tick)
            self._ticks_since_rebalance = 0

        # 6. Metrics snapshot
        self.metrics_tracker.snapshot(
            current_tick, self.active_events, self.ambulances
        )

    # ── Core dispatcher actions ────────────────────────────────────────────────

    def assign_task(
        self, ambulance: Ambulance, event: Accident, current_tick: int
    ) -> None:
        """Assign *event* to *ambulance*.

        Steps
        -----
        1. Guard: skip if ambulance is no longer idle.
        2. Compute traffic-aware A* path.
        3. Record initial path weight for re-routing baseline (Sprint 7).
        4. Pre-compute pixel polyline and cache it on the ambulance.
        5. Set ambulance navigation state.
        6. Mark event as assigned.
        """
        # Guard: only assign if still idle
        if ambulance.state != AmbulanceState.IDLE:
            return

        # 1. Compute A* path (traffic-aware if model is available)
        path = astar_traffic(
            self.graph,
            ambulance.current_location,
            event.location,
            self.traffic,
        )

        if path is None:
            logger.warning(
                "Event %d at node %d is UNREACHABLE from ambulance %d at node %d. "
                "Skipping assignment.",
                event.id, event.location, ambulance.id, ambulance.current_location,
            )
            event.assigned_ambulance_id = -1
            return

        # 2. Record initial path weight for re-routing (Sprint 7)
        if self.traffic is not None:
            ambulance.path_weight_at_dispatch = self.traffic.path_weight(path)
        else:
            ambulance.path_weight_at_dispatch = float(len(path))
        ambulance.reroute_check_tick = 0

        # 3. Pre-compute pixel polyline and cache on ambulance
        ambulance.pixel_polyline = [
            self._node_to_pixel(n)
            for n in path
            if n in self.node_positions
        ]

        # 4. Set ambulance navigation state (path already computed above)
        ambulance.navigate(destination=event.location, path=path)
        ambulance.assigned_task  = event
        ambulance.dispatch_tick  = current_tick

        # 5. Mark event as assigned
        event.assigned_ambulance_id = ambulance.id
        event.dispatch_tick         = current_tick
        self.assigned_events[event.id] = ambulance.id

        logger.debug(
            "Ambulance %d → Event %d (tick %d, path length %d).",
            ambulance.id, event.id, current_tick, len(path),
        )

    def rebalance_fleet(self, current_tick: int) -> None:
        """Sprint 6 (US-023): HDBSCAN-driven hotspot rebalancing.

        Steps
        -----
        1. Run HDBSCAN via DemandClusterer on all active event locations.
        2. For each hotspot, find the nearest IDLE ambulance that is not
           already rebalancing toward a similar target.
        3. Send chosen ambulances to hotspot centroids in REBALANCING state.
        """
        # Run clustering
        self.hotspots = self._clusterer.run(self.active_events)

        if not self.hotspots:
            logger.debug("Rebalance tick %d: no hotspots found.", current_tick)
            return

        idle_ambs = self.get_idle_ambulances()
        if not idle_ambs:
            logger.debug("Rebalance tick %d: no idle ambulances to rebalance.", current_tick)
            return

        logger.info(
            "Rebalance tick %d: %d hotspot(s), %d idle ambulance(s).",
            current_tick, len(self.hotspots), len(idle_ambs),
        )

        assigned_ambs: set[int] = set()

        for hotspot in self.hotspots:
            if not idle_ambs:
                break

            # Find closest idle ambulance to hotspot centroid
            best_amb: Ambulance | None = None
            best_dist = float("inf")
            for amb in idle_ambs:
                if amb.id in assigned_ambs:
                    continue
                # Skip if already parked at centroid
                if amb.current_location == hotspot.centroid_node:
                    continue
                try:
                    i = self.node_index[amb.current_location]
                    j = self.node_index[hotspot.centroid_node]
                    d = float(self.distance_matrix[i][j])
                except (KeyError, IndexError):
                    d = float("inf")
                if d < best_dist:
                    best_dist = d
                    best_amb  = amb

            if best_amb is None:
                continue

            path = astar_traffic(
                self.graph,
                best_amb.current_location,
                hotspot.centroid_node,
                self.traffic,
            )
            if path is None:
                continue

            best_amb.rebalance_target = hotspot.centroid_node
            best_amb.pixel_polyline   = [
                self._node_to_pixel(n)
                for n in path
                if n in self.node_positions
            ]
            best_amb.navigate(
                destination=hotspot.centroid_node,
                path=path,
                rebalancing=True,
            )
            assigned_ambs.add(best_amb.id)
            # Remove from pool so we don't double-assign
            idle_ambs = [a for a in idle_ambs if a.id not in assigned_ambs]

            logger.info(
                "Ambulance %d → REBALANCING toward hotspot %d centroid node %d.",
                best_amb.id, hotspot.cluster_id, hotspot.centroid_node,
            )

    def complete_event(self, ambulance: Ambulance, current_tick: int) -> None:
        """Called when an ambulance finishes ON_SCENE service."""
        task = ambulance.assigned_task

        if task and not task.resolved:
            spawn_tick    = task.timestamp
            dispatch_tick = getattr(task, "dispatch_tick", current_tick)

            self.metrics_tracker.record_response(
                event_id      = task.id,
                spawn_tick    = spawn_tick,
                dispatch_tick = dispatch_tick,
                arrival_tick  = current_tick,
                priority      = task.priority,
                location_node = task.location,
            )
            task.resolved = True

            # Remove from active queue
            self.active_events = [
                e for e in self.active_events if e.id != task.id
            ]
            if task.id in self.assigned_events:
                del self.assigned_events[task.id]

        # Reset ambulance
        ambulance.assigned_task          = None
        ambulance.current_path           = []
        ambulance.pixel_polyline         = []
        ambulance.dispatch_tick          = None
        ambulance.rebalance_target       = None
        ambulance.reroute_check_tick     = 0
        ambulance.path_weight_at_dispatch = 0.0
        ambulance.state                  = AmbulanceState.IDLE
        ambulance.progress               = 0.0

        # Clear on-scene timer
        self._on_scene_since.pop(ambulance.id, None)

        logger.debug(
            "Ambulance %d completed task at tick %d; returning to IDLE.",
            ambulance.id, current_tick,
        )

    # ── Sprint 7: congestion re-routing ───────────────────────────────────────

    def _check_rerouting(self, current_tick: int) -> None:
        """For each IN_TRANSIT ambulance, check if congestion warrants re-route.

        Trigger condition (US-026):
            remaining_weight ≥ path_weight_at_dispatch × (1 + threshold)

        Logged with reason ``'CONGESTION_DETECTED'``.
        """
        if self.traffic is None:
            return

        for amb in self.ambulances:
            if amb.state != AmbulanceState.IN_TRANSIT:
                continue
            if not amb.assigned_task:
                continue

            # Rate-limit checks per ambulance
            if current_tick - amb.reroute_check_tick < self._reroute_check_interval:
                continue
            amb.reroute_check_tick = current_tick

            remaining_path = amb.current_path
            if len(remaining_path) < 2:
                continue

            current_weight = self.traffic.path_weight(remaining_path)
            baseline       = amb.path_weight_at_dispatch

            if baseline <= 0:
                continue

            increase_ratio = (current_weight - baseline) / baseline
            if increase_ratio >= self._reroute_threshold:
                logger.info(
                    "CONGESTION_DETECTED: Ambulance %d re-routing "
                    "(weight increase %.1f%%, threshold %.1f%%).",
                    amb.id,
                    increase_ratio * 100,
                    self._reroute_threshold * 100,
                )
                self._reroute_ambulance(amb, current_tick)

    def _reroute_ambulance(self, amb: Ambulance, current_tick: int) -> None:
        """Recompute A* from ambulance's current location to its assigned event."""
        if not amb.assigned_task:
            return

        destination = amb.assigned_task.location
        new_path = astar_traffic(
            self.graph,
            amb.current_location,
            destination,
            self.traffic,
        )
        if new_path is None:
            return   # Cannot re-route; keep existing path

        # Update path and re-baseline weight
        amb.current_path             = new_path
        amb.path_weight_at_dispatch  = self.traffic.path_weight(new_path) if self.traffic else float(len(new_path))
        amb.pixel_polyline           = [
            self._node_to_pixel(n)
            for n in new_path
            if n in self.node_positions
        ]
        amb.progress = 0.0
        logger.debug(
            "Ambulance %d re-routed at tick %d; new path length %d.",
            amb.id, current_tick, len(new_path),
        )

    # ── State query helpers ────────────────────────────────────────────────────

    def get_idle_ambulances(self) -> list[Ambulance]:
        """Return all ambulances currently in IDLE state."""
        return [a for a in self.ambulances if a.state == AmbulanceState.IDLE]

    def get_unassigned_events(self) -> list[Accident]:
        """Return active events that have no ambulance assigned and are not resolved."""
        return [
            e for e in self.active_events
            if e.assigned_ambulance_id is None and not e.resolved
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _node_to_pixel(self, node_id: int) -> tuple[int, int]:
        """Convert a graph node ID to pixel coordinates."""
        pos = self.node_positions[node_id]
        if isinstance(pos, dict):
            return (int(pos.get("x", pos.get(0, 0))), int(pos.get("y", pos.get(1, 0))))
        return (int(pos[0]), int(pos[1]))
