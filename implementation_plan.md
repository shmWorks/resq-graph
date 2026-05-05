# Migration to Pygame Visualization (Sprints 1-3)

This plan outlines the steps to replace the static Matplotlib visualizations with a dynamic, interactive Pygame-based system for the first three sprints of the ResQ-Graph project.

## User Review Required

> [!IMPORTANT]
> The coordinate system will shift from geographic (lat/lon) to pixel-based for rendering. A conversion utility will be central to this migration.

> [!NOTE]
> Matplotlib will still be used for offline analysis (convergence plots, etc.), but all real-time/interactive maps will move to Pygame.

## Proposed Changes

### Sprint 1: Map Infrastructure & Pixel Mapping

#### [MODIFY] [map_loader.py](file:///c:/Users/Mumtaz/resq-graph/src/map_loader.py)
- Add `render_to_png(G, path)` to save the street network as `map_bg.png`.
- Add logic to save `node_positions.json` (node ID -> pixel x, y).

#### [NEW] [map_config.py](file:///c:/Users/Mumtaz/resq-graph/src/map_config.py)
- Define `SCREEN_WIDTH` (1200), `SCREEN_HEIGHT` (900).
- Implement `latlon_to_pixel(lat, lon, bbox)` conversion logic.

---

### Sprint 2: Navigation & Interactive Path Viewer

#### [NEW] [draw_path.py](file:///c:/Users/Mumtaz/resq-graph/src/draw_path.py)
- Implement `draw_path(surface, node_list, color, node_positions)`.
- Implement `PygameViewer` class to handle:
    - Background blitting (`map_bg.png`).
    - Zoom and Pan (mouse scroll/drag).
    - Event loop (ESC to quit).

#### [MODIFY] [visualizer.py](file:///c:/Users/Mumtaz/resq-graph/src/visualizer.py)
- Refactor to wrap the new `PygameViewer` instead of using `osmnx.plot_graph` (which uses Matplotlib).

---

### Sprint 3: Strategic Solver & Dynamic Overlays

#### [MODIFY] [run_genetic_algorithm.py](file:///c:/Users/Mumtaz/resq-graph/src/run_genetic_algorithm.py)
- Replace `visualize_stations` Matplotlib logic with `PygameViewer`.
- Add logic to render Voronoi regions as translucent polygons on an alpha Surface.
- Implement keyboard toggles:
    - `V`: Toggle coverage zones.
    - `C`: Toggle Random vs. Optimal comparison.
    - `S`: Save screenshot.

## Verification Plan

### Automated Tests
- Unit tests for `latlon_to_pixel` to ensure coordinates stay within `SCREEN_WIDTH` and `SCREEN_HEIGHT`.
- Script to verify `node_positions.json` contains all nodes in `model_town.graphml`.

### Manual Verification
- Run `bake_map.py` and verify `map_bg.png` looks correct.
- Run Sprint 2 test cases and verify path drawing in Pygame with zoom/pan.
- Run GA and verify optimal station markers (stars) and translucent coverage zones.
