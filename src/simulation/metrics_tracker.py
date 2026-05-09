"""
metrics_tracker.py – Sprint 5 (US-019)

Tracks response times per event, computes Average Response Time (ART),
maintains a per-tick history for the Pygame HUD, and exports data to CSV.
"""
import csv
import math
import os
import logging
from collections import deque

from src.config import (
    METRICS_CSV_PATH,
    METRICS_SUMMARY_PATH,
    METRICS_FLUSH_INTERVAL,
)
from src.simulation.ambulance import AmbulanceState

logger = logging.getLogger(__name__)

# CSV column order for per-event log
_EVENT_FIELDS = [
    "event_id", "spawn_tick", "dispatch_tick", "arrival_tick",
    "response_time", "priority", "location_node",
]


class MetricsTracker:
    """Collects, computes, and exports simulation performance metrics.

    Response time definition (Sprint 5):
        response_time = arrival_tick - spawn_tick

    Both queue_wait (dispatch_tick - spawn_tick) and travel_time
    (arrival_tick - dispatch_tick) are also stored in the CSV for analysis.
    """

    def __init__(
        self,
        csv_path: str = METRICS_CSV_PATH,
        summary_path: str = METRICS_SUMMARY_PATH,
        flush_interval: int = METRICS_FLUSH_INTERVAL,
    ):
        self.csv_path       = csv_path
        self.summary_path   = summary_path
        self.flush_interval = flush_interval

        self.response_times: list[float] = []
        self._buffer:        list[dict]  = []
        self._tick_history:  deque       = deque(maxlen=200)  # HUD sparkline
        self._ticks_since_flush          = 0
        self._rt_sum:        float       = 0.0   # US-048: running sum for O(1) ART

        # Ensure output directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def record_response(
        self,
        event_id:     int,
        spawn_tick:   int,
        dispatch_tick: int,
        arrival_tick: int,
        priority:     int = 0,
        location_node: int = 0,
    ) -> None:
        """Compute and buffer one response-time entry.

        Called by ``DispatcherBrain.complete_event()`` each time an ambulance
        finishes attending a scene.
        """
        rt = arrival_tick - spawn_tick
        self.response_times.append(rt)
        self._rt_sum += rt   # US-048: keep running total
        self._buffer.append({
            "event_id":      event_id,
            "spawn_tick":    spawn_tick,
            "dispatch_tick": dispatch_tick,
            "arrival_tick":  arrival_tick,
            "response_time": rt,
            "priority":      priority,
            "location_node": location_node,
        })

        self._ticks_since_flush += 1
        if self._ticks_since_flush >= self.flush_interval:
            self.flush_csv()
            self._ticks_since_flush = 0

    @property
    def art(self) -> float:
        """Average Response Time across all resolved events. O(1) via running sum."""
        return (
            self._rt_sum / len(self.response_times)
            if self.response_times
            else 0.0
        )

    def snapshot(
        self, current_tick: int, active_events: list, ambulances: list
    ) -> None:
        """Record per-tick aggregate metrics for HUD display."""
        self._tick_history.append({
            "tick":        current_tick,
            "art":         self.art,
            "active":      len(active_events),
            "utilisation": self._utilisation(ambulances),
        })

    def flush_csv(self) -> None:
        """Append buffered event rows to the per-event CSV."""
        if not self._buffer:
            return
        file_exists = os.path.isfile(self.csv_path)
        try:
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_EVENT_FIELDS)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(self._buffer)
            self._buffer.clear()
        except OSError as exc:
            logger.warning("Could not write metrics CSV: %s", exc)

    def export_summary_csv(self) -> None:
        """Write final summary statistics to a separate CSV on simulation exit."""
        if not self.response_times:
            logger.info("No events resolved; skipping summary CSV export.")
            return
        rt  = self.response_times
        avg = self.art
        std = math.sqrt(sum((x - avg) ** 2 for x in rt) / len(rt))
        summary = {
            "total_events": len(rt),
            "art":          round(avg, 3),
            "std_dev":      round(std, 3),
            "min_rt":       min(rt),
            "max_rt":       max(rt),
        }
        try:
            with open(self.summary_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
                writer.writeheader()
                writer.writerow(summary)
            logger.info("Summary CSV written to %s", self.summary_path)
        except OSError as exc:
            logger.warning("Could not write summary CSV: %s", exc)

    def get_hud_data(self) -> dict:
        """Return a dict consumed by PygameRenderer for HUD and metrics panel."""
        rt = self.response_times
        return {
            "art":          round(self.art, 2),
            "total_events": len(rt),
            "latest_rt":    rt[-1] if rt else 0,
            "min_rt":       min(rt) if rt else 0,
            "max_rt":       max(rt) if rt else 0,
            "std_dev":      round(
                math.sqrt(sum((x - self.art) ** 2 for x in rt) / len(rt)), 2
            ) if len(rt) > 1 else 0.0,
            "last_five":    rt[-5:] if rt else [],
            "tick_history": list(self._tick_history),
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _utilisation(self, ambulances: list) -> float:
        """Fleet utilisation as a percentage (0–100)."""
        if not ambulances:
            return 0.0
        non_idle = sum(
            1 for a in ambulances if a.state != AmbulanceState.IDLE
        )
        return round((non_idle / len(ambulances)) * 100, 1)
