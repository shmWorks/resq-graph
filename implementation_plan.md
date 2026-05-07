# Merged Implementation Plan: Sprints 6 & 7 – Dynamic Optimization & Simulation Realism

**Sprint Goal:** Implement advanced dynamic intelligence using HDBSCAN (from scratch) for demand clustering, integrate realistic traffic congestion with real-time re-routing, and finalize the simulation infrastructure with a centralized configuration and logging system.  
**Duration:** Weeks 6-7 (Merged)  
**Total Story Points:** 35  
**Visualization Stack:** Pygame (Live) + Matplotlib (Offline)

---

## User Review Required

> [!IMPORTANT]
> **Algorithm Change Decision:** Per user request, we are replacing K-Means with **HDBSCAN** for hotspot detection. 
> - **Traceability:** This replaces US-021 and US-039 (Sprint 10).
> - **Impact on Sprint 10:** The sensitivity analysis for `k` in US-039 will be replaced with a sensitivity analysis for `min_cluster_size` and `min_samples`.

> [!NOTE]
> **Ambulance State Change:** We are formally introducing a `REBALANCING` state to the ambulance state machine. This allows the dispatcher to track ambulances moving toward hotspots without conflating them with `IN_TRANSIT` (emergency response) or `IDLE` (stationary) states.

---

## Table of Contents

1. [Sprint Overview](#sprint-overview)
2. [Render Layer Stack](#render-layer-stack)
3. [Module 1: HDBSCAN Clustering & Rebalancing (Sprint 6)](#module-1-hdbscan-clustering--rebalancing)
4. [Module 2: Traffic Dynamics & Re-routing (Sprint 7)](#module-2-traffic-dynamics--re-routing)
5. [Module 3: Config & Logging Infrastructure (Sprint 7)](#module-3-config--logging-infrastructure)
6. [Testing & Verification](#testing--verification)
7. [Definition of Done](#definition-of-done)

---

## Sprint Overview

| User Story | Title | Points | Component |
|---|---|---|---|
| **US-021** | Implement HDBSCAN from Scratch | 10 | Intelligence |
| **US-022** | Create Demand Clustering Module | 4 | Intelligence |
| **US-023** | Integrate Hotspot Rebalancing into Dispatcher | 5 | Simulation |
| **US-024** | Visualize Hotspots & Clusters (Pygame) | 4 | Rendering |
| **US-025** | Traffic Congestion Simulation (Edge Dynamics) | 6 | Simulation |
| **US-026** | Ambulance Re-routing on Path | 4 | Simulation |
| **US-027** | Simulation Parameter Configuration (YAML) | 3 | Infra |
| **US-028** | Comprehensive Simulation Logging System | 3 | Infra |
| **Total** | | **39** | |

---

## Render Layer Stack

To ensure visual consistency and performance, all rendering must follow this Z-order:

| Layer | Component | Source | Optimization |
|---|---|---|---|
| **0** | Map Background | `map_bg.png` | Static Blit |
| **1** | Congestion Heatmap | **Sprint 7** | **Cached Surface** (only redraw on weight change) |
| **2** | Accident Markers | Sprint 4 | Redraw per tick |
| **3** | Hotspot Convex Hulls | **Sprint 6** | Redraw per tick (Alpha Surface) |
| **4** | Hotspot Pulsing Circles | **Sprint 6** | Redraw per tick |
| **5** | Ambulance Paths | Sprint 5 | Dashed lines |
| **6** | Ambulance Sprites | Sprint 4 | Sprites with state-colors |
| **7** | HUD / Log Strip | **Sprint 7** | Text Rendering |
| **8** | Metrics / Log History | Sprint 5/7 | Toggleable Overlays (`M`, `L`) |

---

## Module 1: HDBSCAN Clustering & Rebalancing

### US-021: HDBSCAN Module (From Scratch)
- **Goal:** Manual implementation of density-based clustering.
- **Implementation Standard:** The implementation should be as efficient, optimized, robust, clean, and self-documenting as a professional library API (e.g., `scikit-learn`), avoiding premature optimization (Hoare's Maxim) while ensuring high performance on simulation-sized datasets.
- **Steps:**
  1. **Core Distance:** Find distance to $k$-th neighbor ($k = \text{min\_samples}$).
  2. **Mutual Reachability:** $d_{mre}(a, b) = \max(\text{core}_a, \text{core}_b, \text{dist}(a, b))$.
  3. **MST:** Build Minimum Spanning Tree using $d_{mre}$.
  4. **Condense Tree:** Collapse hierarchy based on `min_cluster_size`.
  5. **Stability Extraction:** Select clusters by maximizing "Excess of Mass".

### US-022: Demand Clustering Module
- **Acceptance Criteria:**
  - Input: List of active accident locations.
  - Output: List of `Hotspot` objects containing `(node_id, pixel_pos)` tuples.
  - Centroids calculated as geometric mean of cluster members.

### US-023: Dispatcher Rebalancing
- **Acceptance Criteria:**
  - Every `rebalance_interval` (default 50), run HDBSCAN.
  - Assign `IDLE` ambulances to navigate to hotspot centroids.
  - **New State:** Transition ambulance to `REBALANCING` state while moving.
  - Ensure rebalancing does not interrupt existing `IN_TRANSIT` assignments.

### US-024: Hotspot Visualization
- **Acceptance Criteria:**
  - Pulsing blue circles at centroids.
  - Translucent shaded convex hulls for cluster boundaries.
  - **Interaction:** Press **H** to toggle hotspot overlay on/off.

---

## Module 2: Traffic Dynamics & Re-routing

### US-025: Traffic Congestion Simulation
- **Acceptance Criteria:**
  - Weight Multiplier: 1.0 (free) to 2.5 (max congestion).
  - Congestion increases with local event density and decays over time.
  - **Visualization:** Roads colored Green → Yellow → Red.
  - **Optimization:** Use a cached `pygame.Surface` for the heatmap layer.
  - **Interaction:** Press **T** to toggle traffic overlay on/off.

### US-026: Ambulance Re-routing
- **Acceptance Criteria:**
  - In-transit ambulances check path weight every $N$ ticks.
  - **Trigger:** Re-route if the remaining path weight has **increased by ≥ 20%**.
  - Re-routing logged with reason: `"CONGESTION_DETECTED"`.

---

## Module 3: Config & Logging Infrastructure

### US-027: Simulation Parameter Configuration
- **Acceptance Criteria:**
  - Support `SCREEN_W`, `SCREEN_H`, and `TARGET_FPS`.
  - Support `profiles:` in YAML (e.g., `default`, `headless`, `high_stress`).
  - Headless profile must set `SDL_VIDEODRIVER: dummy` (Note: this must be set in `os.environ` before `pygame.init()`).

### US-028: Comprehensive Logging
- **Acceptance Criteria:**
  - Multi-level logging (DEBUG, INFO, WARNING) to console and file.
  - **Log Strip:** Bottom-of-screen Pygame overlay showing last 5 events.
  - **Interaction:** Press **L** to expand/collapse the full log history overlay.

---

## Testing & Verification

### Automated Tests
- **Reroute Threshold:** Assert that a 15% increase does *not* trigger re-route, but 25% *does*.
- **State Machine:** Assert `IDLE` -> `REBALANCING` -> `IDLE` transition on arrival at hotspot.
- **Centroid Logic:** Assert `pixel_pos` matches the mapped coordinates of the `node_id`.

### Manual Verification
- Verify **H**, **T**, and **L** keys toggle their respective layers.
- Verify simulation runs in `--headless` mode using the config profile.

---

## Execution Strategy

> [!NOTE]
> **Progress Tracking:** Upon approval of this plan, a `task.md` will be created in the artifact directory to track granular progress across all modules.
