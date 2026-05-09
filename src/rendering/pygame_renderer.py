"""
pygame_renderer.py – Sprint 6 & 7

Rendering changes from Sprint 5:
- Layer 1 (NEW): Congestion heatmap cached Surface (Sprint 7, US-025, T key).
- Layer 3 (NEW): Hotspot convex hulls (translucent, Sprint 6, US-024).
- Layer 4 (NEW): Hotspot pulsing circles at centroids (Sprint 6, US-024, H key).
- Layer 7 (NEW): HUD log strip – last 5 events (Sprint 7, US-028).
- Layer 8 (NEW): Full log history overlay toggled by L key (Sprint 7, US-028).
- Ambulance colour now covers REBALANCING state (Sprint 6).

draw() signature updated:
    draw(state, ambulances, dispatcher,
         show_metrics_panel, show_hotspots, show_traffic, show_log,
         log_buffer, current_tick)
"""
from __future__ import annotations

import math
import pygame

from src.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    COLOUR_IDLE,
    COLOUR_TRANSIT,
    COLOUR_ON_SCENE,
    COLOUR_ACCIDENT,
    HUD_BG_COLOUR,
    HUD_TEXT_COLOUR,
    DASHED_LINE_COLOUR,
    DASHED_SEGMENT_LEN,
    DASHED_GAP_LEN,
    METRICS_PANEL_WIDTH,
    METRICS_PANEL_HEIGHT,
)
from src.simulation.ambulance import AmbulanceState

# Sprint 6/7 colour additions
COLOUR_REBALANCING  = (100, 100, 255)   # blue – rebalancing ambulance
COLOUR_HOTSPOT_FILL = (0,   120, 255,  40)   # translucent blue hull fill
COLOUR_HOTSPOT_LINE = (0,   160, 255, 180)   # hull outline
COLOUR_TRAFFIC_FREE = (0,   200,   0)        # free-flow green
COLOUR_TRAFFIC_MED  = (255, 200,   0)        # mid congestion yellow
COLOUR_TRAFFIC_JAM  = (220,  30,  30)        # heavy congestion red
LOG_STRIP_BG        = (10,  10,  10, 200)    # dark semi-transparent


def _lerp_colour(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linear interpolate between two RGB colours."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _congestion_colour(multiplier: float, max_mult: float = 2.5) -> tuple:
    """Map a congestion multiplier to an RGB colour (green → yellow → red)."""
    t = max(0.0, min(1.0, (multiplier - 1.0) / (max_mult - 1.0)))
    if t < 0.5:
        return _lerp_colour(COLOUR_TRAFFIC_FREE, COLOUR_TRAFFIC_MED, t * 2)
    return _lerp_colour(COLOUR_TRAFFIC_MED, COLOUR_TRAFFIC_JAM, (t - 0.5) * 2)


class PygameRenderer:
    """Renders the simulation to a Pygame surface.

    Layer order (Sprint 6/7)
    ------------------------
    0  Background map              (static blit)
    1  Congestion heatmap          (cached Surface, T key)
    2  Accident markers            (red X)
    3  Hotspot convex hulls        (translucent, H key)
    4  Hotspot pulsing circles     (H key)
    5  Ambulance path polylines    (dashed blue)
    6  Ambulance sprites
    7  HUD panel                   (top-right)
    8  Metrics panel overlay       (M key)
    9  Log strip                   (bottom of screen)
   10  Log history overlay         (L key)
    """

    def __init__(self, screen: pygame.Surface, node_positions: dict,
                 bg_image_path: str = "data/map_bg.png"):
        self.screen         = screen
        self.node_positions = node_positions

        # ── Background ─────────────────────────────────────────────────────
        try:
            bg_image   = pygame.image.load(bg_image_path).convert()
            self.orig_size = bg_image.get_size()
        except (pygame.error, FileNotFoundError):
            bg_image   = pygame.Surface((1, 1))
            self.orig_size = (1200, 900)  # fallback to standard sim size
        
        self.padding    = 40
        sw, sh          = screen.get_size()
        self.drawable_w = max(1, sw - 2 * self.padding)
        self.drawable_h = max(1, sh - 2 * self.padding)
        self.background = pygame.transform.scale(bg_image, (self.drawable_w, self.drawable_h))

        # Coordinate mapping factors
        self.scale_x = self.drawable_w / self.orig_size[0]
        self.scale_y = self.drawable_h / self.orig_size[1]

        # ── Fonts ──────────────────────────────────────────────────────────
        pygame.font.init()
        self.font        = pygame.font.SysFont("monospace", 16)
        self.font_small  = pygame.font.SysFont("monospace", 14)
        self.font_title  = pygame.font.SysFont("monospace", 16, bold=True)

        # ── Sprint 7: cached traffic heatmap surface ───────────────────────
        self._traffic_cache:        pygame.Surface | None = None
        self._traffic_cache_dirty:  bool = True

        # ── Sprint 6: pulse animation state ───────────────────────────────
        self._pulse_tick = 0

        # ── Sprint 12: sprite cache (US-047) ─────────────────────────────
        # Key: (state_value, amb_id) → pre-rendered Surface with convert_alpha()
        self._sprite_cache: dict[tuple, pygame.Surface] = {}

        # ── Sprint 12: HUD cache (US-047) ────────────────────────────────
        self._hud_cache:     pygame.Surface | None = None
        self._hud_cache_key: tuple | None = None

    def _to_screen(self, pos: tuple) -> tuple:
        """Map raw map coordinates to current screen pixels."""
        return (
            int(pos[0] * self.scale_x + self.padding),
            int(pos[1] * self.scale_y + self.padding)
        )

    # ── Public draw entry point ────────────────────────────────────────────────

    def draw(
        self,
        state,
        ambulances:          list,
        dispatcher           = None,
        show_metrics_panel:  bool = False,
        show_hotspots:       bool = True,
        show_traffic:        bool = True,
        show_log:            bool = False,
        log_buffer           = None,
        current_tick:        int  = 0,
        debug_timing:        bool = False,   # US-045: per-layer ms timing
    ) -> None:
        """Render one frame."""
        import time as _time
        _t = _time.perf_counter if debug_timing else None
        _ts: dict = {}

        active_events = dispatcher.active_events if dispatcher else []
        hud_data      = (
            dispatcher.metrics_tracker.get_hud_data() if dispatcher else {}
        )
        traffic   = getattr(dispatcher, "traffic", None) if dispatcher else None
        hotspots  = getattr(dispatcher, "hotspots", []) if dispatcher else []
        idle_count = sum(1 for a in ambulances if a.state == AmbulanceState.IDLE)
        self._pulse_tick = current_tick

        # ── Layer 0: Background ────────────────────────────────────────────
        if debug_timing: _ts['t0'] = _t()
        self.screen.fill((26, 26, 46))
        self.screen.blit(self.background, (self.padding, self.padding))
        if debug_timing: _ts['bg'] = (_t() - _ts['t0']) * 1000

        # ── Layer 1: Congestion heatmap ────────────────────────────────────
        if debug_timing: _ts['t1'] = _t()
        if show_traffic and traffic is not None:
            self._draw_traffic_heatmap(traffic)
        if debug_timing: _ts['traffic'] = (_t() - _ts['t1']) * 1000

        # ── Layer 2: Accident markers ──────────────────────────────────────
        if debug_timing: _ts['t2'] = _t()
        for event in active_events:
            self._draw_accident(self._to_screen(event.pixel_pos))
        if debug_timing: _ts['events'] = (_t() - _ts['t2']) * 1000

        # ── Layer 3 & 4: Hotspot overlays ─────────────────────────────────
        if debug_timing: _ts['t3'] = _t()
        if show_hotspots and hotspots:
            self._draw_hotspot_hulls(hotspots)
            self._draw_hotspot_circles(hotspots, current_tick)
        if debug_timing: _ts['hotspots'] = (_t() - _ts['t3']) * 1000

        # ── Layer 5: Ambulance path polylines ─────────────────────────────
        if debug_timing: _ts['t5'] = _t()
        self.draw_ambulance_paths(ambulances)
        if debug_timing: _ts['paths'] = (_t() - _ts['t5']) * 1000

        # ── Layer 6: Ambulance sprites ────────────────────────────────────
        if debug_timing: _ts['t6'] = _t()
        for amb in ambulances:
            self._draw_ambulance(amb)
        if debug_timing: _ts['sprites'] = (_t() - _ts['t6']) * 1000

        # ── Layer 7: HUD panel ─────────────────────────────────────────────
        if debug_timing: _ts['t7'] = _t()
        self._draw_hud(state, ambulances, idle_count, hud_data, show_hotspots, show_traffic)
        if debug_timing: _ts['hud'] = (_t() - _ts['t7']) * 1000

        # ── Layer 8: Metrics panel overlay ────────────────────────────────
        if show_metrics_panel:
            self.draw_metrics_panel(hud_data, len(active_events))

        # ── Layer 10: Full log history overlay ────────────────────────────
        if show_log and log_buffer is not None:
            self._draw_log_history(log_buffer)

        if debug_timing:
            total = sum(v for k, v in _ts.items() if not k.startswith('t'))
            print(f"[Render] bg={_ts.get('bg',0):.1f}ms "
                  f"traffic={_ts.get('traffic',0):.1f}ms "
                  f"events={_ts.get('events',0):.1f}ms "
                  f"hotspots={_ts.get('hotspots',0):.1f}ms "
                  f"paths={_ts.get('paths',0):.1f}ms "
                  f"sprites={_ts.get('sprites',0):.1f}ms "
                  f"hud={_ts.get('hud',0):.1f}ms "
                  f"total={total:.1f}ms")


    # ── Layer 1: Traffic heatmap (US-025) ──────────────────────────────────────

    def _draw_traffic_heatmap(self, traffic) -> None:
        """Draw coloured road segments based on their congestion multiplier.

        Uses a cached Surface that is rebuilt only when edges change weight.
        The cache is invalidated externally by setting
        ``renderer._traffic_cache_dirty = True`` after ``traffic.update()``.
        """
        # Rebuild cache if dirty or not yet created
        if self._traffic_cache is None or self._traffic_cache_dirty:
            sw, sh = self.screen.get_size()
            cache = pygame.Surface((sw, sh), pygame.SRCALPHA)
            cache.fill((0, 0, 0, 0))

            for key, mult in traffic.edge_multipliers.items():
                nodes = list(key)
                if len(nodes) != 2:
                    continue
                u, v = nodes[0], nodes[1]
                pos_u = self.node_positions.get(u)
                pos_v = self.node_positions.get(v)
                if pos_u is None or pos_v is None:
                    continue
                colour = _congestion_colour(mult)
                # Draw a thicker coloured line under the road
                p_u = self._to_screen(pos_u)
                p_v = self._to_screen(pos_v)
                pygame.draw.line(
                    cache, colour,
                    p_u, p_v,
                    4,
                )
            self._traffic_cache       = cache
            self._traffic_cache_dirty = False

        self.screen.blit(self._traffic_cache, (0, 0))

    def invalidate_traffic_cache(self) -> None:
        """Call this after traffic.update() to force a heatmap redraw."""
        self._traffic_cache_dirty = True

    # ── Layer 3: Hotspot convex hulls (US-024) ─────────────────────────────────

    def _draw_hotspot_hulls(self, hotspots: list) -> None:
        """Draw a translucent convex hull polygon around each hotspot cluster."""
        for hs in hotspots:
            pts = hs.member_pixel_positions
            if len(pts) < 3:
                # Too few points for a proper hull: draw a circle instead
                if pts:
                    cx, cy = self._to_screen(pts[0])
                    surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                    pygame.draw.circle(surf, COLOUR_HOTSPOT_FILL, (30, 30), 30)
                    self.screen.blit(surf, (cx - 30, cy - 30))
                continue

            hull = [self._to_screen(p) for p in self._convex_hull(pts)]
            if len(hull) < 3:
                continue

            # Draw filled polygon on alpha surface
            sw, sh = self.screen.get_size()
            hull_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.polygon(hull_surf, COLOUR_HOTSPOT_FILL, hull)
            pygame.draw.polygon(hull_surf, COLOUR_HOTSPOT_LINE, hull, 2)
            self.screen.blit(hull_surf, (0, 0))

    @staticmethod
    def _convex_hull(points: list[tuple]) -> list[tuple]:
        """Graham scan convex hull over a list of (x, y) integer tuples."""
        pts = sorted(set(points))
        if len(pts) <= 1:
            return pts

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower: list = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        upper: list = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return lower[:-1] + upper[:-1]

    # ── Layer 4: Hotspot pulsing circles (US-024) ──────────────────────────────

    def _draw_hotspot_circles(self, hotspots: list, tick: int) -> None:
        """Draw animated pulsing blue circles at hotspot centroids."""
        pulse = abs(math.sin(tick * 0.05))   # 0.0 → 1.0 oscillation
        radius = int(10 + pulse * 8)

        for hs in hotspots:
            cx, cy = self._to_screen(hs.pixel_pos)
            # Outer glow ring
            pygame.draw.circle(
                self.screen,
                (50, 130, 255, 120),
                (cx, cy),
                radius + 6,
                2,
            )
            # Solid centre
            pygame.draw.circle(self.screen, (80, 160, 255), (cx, cy), radius)
            pygame.draw.circle(self.screen, (200, 230, 255), (cx, cy), radius, 2)

            # Cluster-size label
            lbl = self.font_small.render(f"H{hs.cluster_id}:{hs.size}", True, (255, 255, 255))
            self.screen.blit(lbl, (cx + radius + 4, cy - 8))

    # ── Layer 2: Accidents ─────────────────────────────────────────────────────

    def _draw_accident(self, pixel_pos: tuple) -> None:
        x, y = int(pixel_pos[0]), int(pixel_pos[1])
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x-6, y-6), (x+6, y+6), 2)
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x-6, y+6), (x+6, y-6), 2)

    # ── Layer 5: Dashed path polylines ────────────────────────────────────────

    def draw_ambulance_paths(self, ambulances: list) -> None:
        """Draw dashed path polylines for all IN_TRANSIT / REBALANCING ambulances."""
        for amb in ambulances:
            if not amb.pixel_polyline or amb.state == AmbulanceState.IDLE:
                continue
            colour = (
                COLOUR_REBALANCING
                if amb.state == AmbulanceState.REBALANCING
                else DASHED_LINE_COLOUR
            )
            screen_poly = [self._to_screen(p) for p in amb.pixel_polyline]
            self._draw_dashed_polyline(self.screen, colour, screen_poly)

    def _draw_dashed_polyline(
        self, surface: pygame.Surface, colour: tuple, points: list[tuple]
    ) -> None:
        for i in range(len(points) - 1):
            self._draw_dashed_segment(surface, colour, points[i], points[i + 1])

    def _draw_dashed_segment(
        self,
        surface: pygame.Surface,
        colour:  tuple,
        p1:      tuple,
        p2:      tuple,
    ) -> None:
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length
        step   = DASHED_SEGMENT_LEN + DASHED_GAP_LEN
        pos    = 0.0
        draw   = True
        while pos < length:
            end = min(pos + DASHED_SEGMENT_LEN, length)
            if draw:
                start_pt = (int(p1[0] + ux * pos), int(p1[1] + uy * pos))
                end_pt   = (int(p1[0] + ux * end), int(p1[1] + uy * end))
                pygame.draw.line(surface, colour, start_pt, end_pt, 2)
            pos  += step
            draw  = not draw

    # ── Layer 6: Ambulances ────────────────────────────────────────────────────

    def _draw_ambulance(self, amb) -> None:
        """Blit a cached sprite for this ambulance (US-047: convert_alpha cache)."""
        key = (amb.state.value, amb.id)
        if key not in self._sprite_cache:
            surf = pygame.Surface((28, 20), pygame.SRCALPHA)
            if amb.state == AmbulanceState.IDLE:
                colour = COLOUR_IDLE
            elif amb.state == AmbulanceState.IN_TRANSIT:
                colour = COLOUR_TRANSIT
            elif amb.state == AmbulanceState.REBALANCING:
                colour = COLOUR_REBALANCING
            else:
                colour = COLOUR_ON_SCENE
            pygame.draw.circle(surf, colour, (8, 10), 8)
            pygame.draw.circle(surf, (0, 0, 0), (8, 10), 8, 1)
            label = self.font_small.render(str(amb.id), True, (255, 255, 255))
            surf.blit(label, (18, 3))
            try:
                self._sprite_cache[key] = surf.convert_alpha()
            except Exception:
                self._sprite_cache[key] = surf
        x, y = self._to_screen(amb.pixel_pos)
        self.screen.blit(self._sprite_cache[key], (x - 8, y - 10))

    # ── Layer 7: HUD panel ─────────────────────────────────────────────────────

    def _draw_hud(
        self,
        state,
        ambulances:    list,
        idle_count:    int,
        hud_data:      dict,
        show_hotspots: bool = True,
        show_traffic:  bool = True,
    ) -> None:
        art         = hud_data.get("art", 0.0)
        total_events = hud_data.get("total_events", 0)
        utilisation = (
            round((1 - idle_count / max(len(ambulances), 1)) * 100)
            if ambulances else 0
        )

        # US-047: only rebuild HUD surface when data changes
        hud_key = (state.current_tick, idle_count, round(art, 2), total_events,
                   state.paused, show_hotspots, show_traffic)
        if hud_key != self._hud_cache_key or self._hud_cache is None:
            hud_w, hud_h = 290, 260
            hud_surf     = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
            hud_surf.fill((*HUD_BG_COLOUR, 200))

            lines = [
                f"Tick:              {state.current_tick}",
                f"Active Events:     {len(getattr(state, 'active_events', []))}",
                f"Idle Ambulances:   {idle_count} / {len(ambulances)}",
                f"Avg Response Time: {art:.1f} ticks",
                f"Events Resolved:   {total_events}",
                f"Fleet Utilisation: {utilisation}%",
                f"Lambda (λ):        {state.lambda_rate:.2f}",
                f"Last HDBSCAN:      tick {state.last_hdbscan_tick}",
                "",
                f"  [H] Hotspots: {'ON ' if show_hotspots else 'OFF'}",
                f"  [T] Traffic:  {'ON ' if show_traffic  else 'OFF'}",
                f"  [M] Metrics   [L] Log",
            ]
            if state.paused:
                lines.insert(0, "  [ ⏸  PAUSED ]")

            y_off = 10
            for line in lines:
                surf = self.font.render(line, True, HUD_TEXT_COLOUR)
                hud_surf.blit(surf, (12, y_off))
                y_off += 20

            self._hud_cache     = hud_surf
            self._hud_cache_key = hud_key

        self.screen.blit(self._hud_cache,
                         (self.screen.get_width() - 300, 10))

    # ── Layer 8: Metrics panel ─────────────────────────────────────────────────

    def draw_metrics_panel(self, hud_data: dict, active_count: int = 0) -> None:
        pw = METRICS_PANEL_WIDTH
        ph = METRICS_PANEL_HEIGHT
        sw, sh = self.screen.get_size()
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 20, 210))

        title = self.font_title.render("  METRICS PANEL  [ M to close ]", True, (180, 220, 255))
        panel.blit(title, (10, 8))
        pygame.draw.line(panel, (80, 80, 80), (10, 28), (pw - 10, 28), 1)

        art          = hud_data.get("art",          0.0)
        std_dev      = hud_data.get("std_dev",       0.0)
        fastest      = hud_data.get("min_rt",        0)
        slowest      = hud_data.get("max_rt",        0)
        total_events = hud_data.get("total_events",  0)
        latest_rt    = hud_data.get("latest_rt",     0)
        last_five    = hud_data.get("last_five",     [])

        rows = [
            ("Average Response Time", f"{art:.2f} ticks"),
            ("Std Deviation",         f"{std_dev:.2f} ticks"),
            ("Fastest Response",      f"{fastest} ticks"),
            ("Slowest Response",      f"{slowest} ticks"),
            ("Total Events Resolved", str(total_events)),
            ("Total Events Pending",  str(active_count)),
            ("Latest Response Time",  f"{latest_rt} ticks"),
            ("Last 5 Response Times", str(last_five) if last_five else "—"),
        ]

        y = 38
        for label, value in rows:
            lbl_surf = self.font_small.render(f"  {label}:", True, (200, 200, 200))
            val_surf = self.font_small.render(value,          True, (255, 255, 100))
            panel.blit(lbl_surf, (10, y))
            panel.blit(val_surf, (pw - val_surf.get_width() - 10, y))
            y += 19

        self.screen.blit(panel, (px, py))

    # ── Layer 9: Log strip (US-028) ────────────────────────────────────────────

    def _draw_log_strip(self, log_buffer) -> None:
        """Draw last 5 log lines at the bottom of the screen."""
        lines = log_buffer.tail(5)
        if not lines:
            return

        strip_h = len(lines) * 18 + 8
        sw, sh  = self.screen.get_size()
        strip_y = sh - strip_h - 4

        strip = pygame.Surface((sw, strip_h), pygame.SRCALPHA)
        strip.fill(LOG_STRIP_BG)

        for i, line in enumerate(lines):
            surf = self.font_small.render(line[:120], True, (180, 220, 180))
            strip.blit(surf, (8, 4 + i * 18))

        self.screen.blit(strip, (0, strip_y))

    # ── Layer 10: Full log history overlay (US-028) ────────────────────────────

    def _draw_log_history(self, log_buffer) -> None:
        """Full-screen semi-transparent log overlay (toggled by L key)."""
        all_lines = log_buffer.all()
        # Show the most recent lines that fit
        sw, sh      = self.screen.get_size()
        max_visible = (sh - 60) // 17
        visible     = all_lines[-max_visible:] if len(all_lines) > max_visible else all_lines

        ow, oh  = sw - 60, sh - 60
        overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 220))

        title = self.font_title.render(
            "  SIMULATION LOG  [ L to close ]", True, (180, 220, 255)
        )
        overlay.blit(title, (10, 8))
        pygame.draw.line(overlay, (80, 80, 80), (10, 28), (ow - 10, 28), 1)

        for i, line in enumerate(visible):
            surf = self.font_small.render(line[:110], True, (200, 220, 200))
            overlay.blit(surf, (10, 34 + i * 17))

        self.screen.blit(overlay, (30, 30))
