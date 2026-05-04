# Sprint 3: Genetic Algorithm & Strategic Solver

**Phase 1: The Skeleton · 21 Points · Est. 12–15 hours**

**Sprint Goal:** Implement facility location optimization using an evolutionary algorithm to find optimal ambulance base station positions across Model Town.

**Dependencies:** Requires data/distance_matrix.npy and data/model_town.graphml from Sprints 1 & 2

---

## US-009: Implement Genetic Algorithm Framework (8 pts)

**GOAL:** Generic GA class that evolves base station locations across the road network graph.

### Checklist

- [ ] Genome representation: list of 5 node IDs (one per ambulance base)
- [ ] Population initialization: 50 random genomes, no duplicate nodes per genome
- [ ] Selection mechanism: fitness-proportionate (roulette wheel selection)
- [ ] Mutation operator: random node swap (replace one base with random graph node)
- [ ] Crossover operator: single-point crossover between two parent genomes
- [ ] GA logic wrapped in a class with clean interface

**Estimated Time:** 3–4 hours

---

## US-010: Implement Fitness Function (Facility Location) (5 pts)

**GOAL:** Fitness function that measures how well a genome (5 base stations) covers all nodes in the graph.

### Checklist

- [ ] Fitness = sum of distances from every node to its nearest base station
- [ ] Distances looked up from distance_matrix.npy — O(1) per lookup
- [ ] Duplicate base stations in a genome are penalized
- [ ] All nodes must be reachable — handle disconnected nodes gracefully
- [ ] Fitness value logged per generation for convergence tracking

**Estimated Time:** 2–3 hours

---

## US-011: Run GA to Convergence & Track Progress (4 pts)

**GOAL:** Execute the GA for 100 generations, track evolution, and export the final optimal station locations.

### Checklist

- [ ] GA runs for 100 generations minimum
- [ ] Best fitness score logged at every generation
- [ ] Convergence plot created with matplotlib (generation vs. best fitness)
- [ ] Final 5 optimal station node IDs recorded and exported (JSON or npy)
- [ ] Total execution time under 2 minutes on Model Town sandbox

**Estimated Time:** 2 hours

---

## US-012: Visualize Optimal Station Locations on Map (4 pts)

**GOAL:** Map visualization comparing optimal GA-evolved stations against random placement, with coverage zones.

### Checklist

- [ ] Street network plotted as light gray background
- [ ] Optimal station locations marked as blue stars (★)
- [ ] Coverage zones visualized — Voronoi regions or heatmap overlay
- [ ] Random station placement shown in gray for side-by-side comparison
- [ ] HTML report generated containing the final visualization

**Estimated Time:** 2–3 hours

---

## Deliverables

| File | Description |
|------|-------------|
| src/genetic_algorithm.py | GA class with population, selection, crossover, mutation |
| src/fitness.py | Fitness function using distance matrix |
| outputs/convergence_plot.png | Generation vs. best fitness chart |
| outputs/optimal_stations.png | Map with optimal + random station comparison |
| outputs/optimal_stations.json | 5 optimal node IDs exported for Sprint 4 |

---

## Success Criteria

- [ ] GA implemented from scratch — no scipy.optimize or sklearn
- [ ] Fitness function uses distance matrix (not live A* calls)
- [ ] Convergence plot shows clear improvement over generations
- [ ] Optimal stations visually better distributed than random placement
- [ ] All output files committed to version control
- [ ] Execution time under 2 minutes end-to-end

---

**Next:** Sprint 4 — Simulation Engine & Ambulance Agents