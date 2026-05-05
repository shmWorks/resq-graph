"""
draw_path.py – Sprint 2: Interactive Pygame path viewer.

Public API
----------
draw_path(surface, node_list, color, node_positions)
    Renders a polyline for a sequence of nodes onto a pygame.Surface.

PygameViewer
    Full-featured interactive map viewer with:
      • Dark street-network background (map_bg.png).
      • Smooth zoom  (mouse-wheel / +/- keys).
      • Pan          (left-click drag).
      • Named path overlays with configurable colours.
      • ESC / window-close to quit.
"""

from __future__ import annotations

import os
import sys
import json
from typing import Sequence

import pygame

from map_config import SCREEN_WIDTH, SCREEN_HEIGHT, latlon_to_pixel

# ── Colour palette ────────────────────────────────────────────────────────────
_BG_COLOUR      = (26,  26,  46)   # #1a1a2e  – dark navy
_GRID_COLOUR    = (51,  65,  85)   # #334155  – slate streets
_DEFAULT_PATH   = (56, 189, 248)   # #38bdf8  – sky-blue path
_START_COLOUR   = (34, 197,  94)   # #22c55e  – green
_GOAL_COLOUR    = (239,  68,  68)  # #ef4444  – red
_MARKER_RADIUS  = 7
_PATH_WIDTH     = 3

# ── Zoom limits ───────────────────────────────────────────────────────────────
ZOOM_MIN = 0.5
ZOOM_MAX = 8.0
ZOOM_STEP = 0.15           # per mouse-wheel tick


# ─────────────────────────────────────────────────────────────────────────────
# draw_path
# ─────────────────────────────────────────────────────────────────────────────

def draw_path(
    surface: pygame.Surface,
    node_list: Sequence,
    color: tuple,
    node_positions: dict,
    width: int = _PATH_WIDTH,
) -> None:
    """Draw a polyline for *node_list* onto *surface*.

    Parameters
    ----------
    surface : pygame.Surface
        Render target (may be a subsurface or the main display).
    node_list : sequence
        Ordered node IDs (strings or ints) that form the path.
    color : tuple
        RGB colour, e.g. ``(56, 189, 248)``.
    node_positions : dict
        ``{str(node_id): [px, py]}`` – the pixel positions loaded from
        ``node_positions.json``.
    width : int
        Line thickness in pixels.
    """
    if len(node_list) < 2:
        return

    pts: list[tuple[int, int]] = []
    for n in node_list:
        pos = node_positions.get(str(n))
        if pos is None:
            continue
        pts.append((pos[0], pos[1]))

    if len(pts) < 2:
        return

    pygame.draw.lines(surface, color, False, pts, width)

    # Start / goal markers
    pygame.draw.circle(surface, _START_COLOUR, pts[0],  _MARKER_RADIUS)
    pygame.draw.circle(surface, _GOAL_COLOUR,  pts[-1], _MARKER_RADIUS)


# ─────────────────────────────────────────────────────────────────────────────
# PygameViewer
# ─────────────────────────────────────────────────────────────────────────────

class PygameViewer:
    """Interactive Pygame map viewer.

    Parameters
    ----------
    node_positions : dict
        ``{str(node_id): [px, py]}``  (pixel positions for the *base* zoom).
    bg_path : str
        Path to the pre-rendered street-network PNG (``map_bg.png``).
    title : str
        Window title.
    """

    # ------------------------------------------------------------------
    def __init__(
        self,
        node_positions: dict,
        bg_path: str | None = None,
        title: str = "ResQ-Graph Viewer",
    ) -> None:
        self.node_positions = node_positions
        self.bg_path = bg_path or os.path.join("data", "map_bg.png")
        self.title = title

        # View state
        self._zoom:   float = 1.0
        self._offset: list[float] = [0.0, 0.0]   # pan offset in pixels
        self._drag_start: tuple[int, int] | None = None
        self._drag_offset_start: list[float] = [0.0, 0.0]

        # Overlays registered via add_path()
        self._paths:  list[dict] = []

        # Extra draw callbacks (used by Sprint 3 for Voronoi etc.)
        self._overlay_callbacks: list = []

        # HUD / key-toggle states (Sprint 3 uses these)
        self.show_coverage  = False
        self.show_comparison = False

        # Pygame objects (created in run())
        self._screen: pygame.Surface | None = None
        self._bg_orig: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._font_sm: pygame.font.Font | None = None
        self._font_md: pygame.font.Font | None = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def add_path(
        self,
        node_list: Sequence,
        color: tuple = _DEFAULT_PATH,
        label: str = "",
        width: int = _PATH_WIDTH,
    ) -> "PygameViewer":
        """Register a path overlay.  Returns *self* for chaining."""
        self._paths.append(
            {"nodes": node_list, "color": color, "label": label, "width": width}
        )
        return self

    def add_overlay_callback(self, fn) -> "PygameViewer":
        """Register an arbitrary draw callback ``fn(surface, viewer)``."""
        self._overlay_callbacks.append(fn)
        return self

    def world_to_screen(self, px: float, py: float) -> tuple[int, int]:
        """Convert a *base-zoom* pixel position to current screen position."""
        sx = int(px * self._zoom + self._offset[0])
        sy = int(py * self._zoom + self._offset[1])
        return sx, sy

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_pygame(self) -> None:
        pygame.init()
        pygame.display.set_caption(self.title)
        self._screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE
        )
        self._clock = pygame.time.Clock()
        self._font_sm = pygame.font.SysFont("segoeui", 13)
        self._font_md = pygame.font.SysFont("segoeui", 16, bold=True)

    def _load_background(self) -> None:
        if os.path.exists(self.bg_path):
            raw = pygame.image.load(self.bg_path).convert()
            self._bg_orig = pygame.transform.smoothscale(
                raw, (SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        else:
            # Fallback: plain dark surface
            self._bg_orig = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self._bg_orig.fill(_BG_COLOUR)
            print(
                f"[PygameViewer] Warning: background not found at '{self.bg_path}'. "
                "Run bake_map.py first."
            )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _build_world_surface(self) -> pygame.Surface:
        """Build the world layer at current zoom level."""
        w = int(SCREEN_WIDTH  * self._zoom)
        h = int(SCREEN_HEIGHT * self._zoom)
        world = pygame.transform.smoothscale(self._bg_orig, (w, h))
        return world

    def _draw_paths_on(self, surface: pygame.Surface) -> None:
        """Render all registered path overlays onto *surface*."""
        # Build a pixel-position dict scaled to the zoomed world
        scaled_pos = {
            k: (int(v[0] * self._zoom), int(v[1] * self._zoom))
            for k, v in self.node_positions.items()
        }

        for entry in self._paths:
            pts = []
            for n in entry["nodes"]:
                p = scaled_pos.get(str(n))
                if p:
                    pts.append(p)
            if len(pts) < 2:
                continue
            pygame.draw.lines(surface, entry["color"], False, pts, entry["width"])
            # Start / goal
            pygame.draw.circle(surface, _START_COLOUR, pts[0],  _MARKER_RADIUS)
            pygame.draw.circle(surface, _GOAL_COLOUR,  pts[-1], _MARKER_RADIUS)

    def _draw_hud(self) -> None:
        """Render the HUD (key hints, zoom level) on top of everything."""
        hints = [
            f"Zoom: {self._zoom:.2f}×   |   Scroll to zoom, drag to pan   |   ESC to quit",
        ]
        if self._overlay_callbacks:
            hints.append("V: coverage zones   C: comparison   S: screenshot")

        y = SCREEN_HEIGHT - 24 * len(hints) - 6
        for line in hints:
            surf = self._font_sm.render(line, True, (148, 163, 184))  # slate-400
            self._screen.blit(surf, (8, y))
            y += 22

        # Legend for paths
        lx, ly = 10, 10
        for entry in self._paths:
            if not entry["label"]:
                continue
            pygame.draw.line(
                self._screen, entry["color"],
                (lx, ly + 8), (lx + 24, ly + 8), 3
            )
            txt = self._font_md.render(entry["label"], True, (226, 232, 240))
            self._screen.blit(txt, (lx + 30, ly))
            ly += 26

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle_zoom(self, delta: float, pivot_x: int, pivot_y: int) -> None:
        """Zoom in/out keeping the cursor position fixed on screen."""
        old_zoom = self._zoom
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom + delta))
        if new_zoom == old_zoom:
            return
        # Adjust offset so the point under the cursor stays stationary
        scale = new_zoom / old_zoom
        self._offset[0] = pivot_x - scale * (pivot_x - self._offset[0])
        self._offset[1] = pivot_y - scale * (pivot_y - self._offset[1])
        self._zoom = new_zoom

    def _handle_events(self) -> bool:
        """Process events; return False when the viewer should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    cx, cy = pygame.mouse.get_pos()
                    self._handle_zoom(+ZOOM_STEP, cx, cy)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    cx, cy = pygame.mouse.get_pos()
                    self._handle_zoom(-ZOOM_STEP, cx, cy)
                elif event.key == pygame.K_v:
                    self.show_coverage = not self.show_coverage
                elif event.key == pygame.K_c:
                    self.show_comparison = not self.show_comparison
                elif event.key == pygame.K_s:
                    self._save_screenshot()

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                self._handle_zoom(event.y * ZOOM_STEP, mx, my)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._drag_start = event.pos
                self._drag_offset_start = list(self._offset)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._drag_start = None

            elif event.type == pygame.MOUSEMOTION:
                if self._drag_start is not None:
                    dx = event.pos[0] - self._drag_start[0]
                    dy = event.pos[1] - self._drag_start[1]
                    self._offset[0] = self._drag_offset_start[0] + dx
                    self._offset[1] = self._drag_offset_start[1] + dy

        return True

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def _save_screenshot(self) -> None:
        import time
        os.makedirs("outputs", exist_ok=True)
        fname = os.path.join(
            "outputs", f"screenshot_{int(time.time())}.png"
        )
        pygame.image.save(self._screen, fname)
        print(f"Screenshot saved: {fname}")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Initialise Pygame and enter the event/render loop."""
        self._init_pygame()
        self._load_background()

        running = True
        while running:
            running = self._handle_events()

            # --- Build world layer ------------------------------------------
            world = self._build_world_surface()
            self._draw_paths_on(world)

            # Custom overlays (Voronoi, station markers …)
            for fn in self._overlay_callbacks:
                fn(world, self)

            # --- Blit world onto screen with pan offset ---------------------
            self._screen.fill(_BG_COLOUR)
            self._screen.blit(world, (int(self._offset[0]), int(self._offset[1])))

            # --- HUD on top -------------------------------------------------
            self._draw_hud()

            pygame.display.flip()
            self._clock.tick(60)

        pygame.quit()


# ─────────────────────────────────────────────────────────────────────────────
# Convenience factory
# ─────────────────────────────────────────────────────────────────────────────

def load_node_positions(path: str = os.path.join("data", "node_positions.json")) -> dict:
    """Load ``node_positions.json`` from disk.

    Returns an empty dict (with a warning) if the file is not found.
    """
    if not os.path.exists(path):
        print(f"[draw_path] Warning: '{path}' not found. Run bake_map.py first.")
        return {}
    with open(path) as f:
        return json.load(f)
