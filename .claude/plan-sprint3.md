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
- [ ] Unit tests for all operators (see Test Strategy below)

**Estimated Time:** 3–4 hours

---

## US-010: Implement Fitness Function (Facility Location) (5 pts)

**GOAL:** Fitness function that measures how well a genome (5 base stations) covers all nodes in the graph.

### Checklist

- [ ] Fitness = sum of distances from every node to its nearest base station
- [ ] Distances looked up from distance_matrix.npy — O(1) per lookup
- [ ] Duplicate base stations in a genome are penalized
- [ ] All nodes must be reachable — handle disconnected nodes gracefully (see Disconnected Node Handling below)
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
| src/run_genetic_algorithm.py | CLI entry point with profiling hooks |
| src/tests/test_genetic_algorithm.py | Unit tests |
| src/tests/test_integration.py | Integration tests |
| src/tests/test_system.py | System/performance tests |
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

## Test Strategy (Required)

### Unit Tests (`src/tests/test_genetic_algorithm.py`)

**Coverage target: 80%**

```python
"""Unit tests for GA operators. KISS + YAGNI."""
import pytest
import numpy as np
from genetic_algorithm import GeneticAlgorithm, Genome

class TestGenomeRepresentation:
    """Genome structure validation."""
    
    def test_no_duplicate_nodes(self):
        """Genome must not contain duplicate node IDs."""
        genome = [1, 2, 3, 4, 5]
        assert len(genome) == len(set(genome))
    
    def test_length_equals_num_stations(self):
        """Genome length must match NUM_STATIONS."""
        genome = [0] * 5
        assert len(genome) == NUM_STATIONS


class TestSelection:
    """Selection operator tests."""
    
    def test_roulette_wheel_returns_valid_genome(self):
        """Selection must return valid genome from population."""
        # ...
    
    def test_fitter_genomes_selected_more_often(self):
        """Higher fitness = higher selection probability."""
        #


class TestCrossover:
    """Crossover operator tests."""
    
    def test_offspring_has_valid_length(self):
        """Offspring length equals parent length."""
        # ...
    
    def test_no_duplicate_nodes_in_offspring(self):
        """Crossover must not create duplicates."""
        #


class TestMutation:
    """Mutation operator tests."""
    
    def test_mutated_genome_stays_in_bounds(self):
        """Mutated node ID must exist in graph."""
        # ...
    
    def test_mutation_rate_respected(self):
        """Only one position mutates per call."""
        #
```

### Integration Tests (`src/tests/test_integration.py`)

```python
"""Integration tests: GA + fitness end-to-end."""
import pytest
from genetic_algorithm import run_genetic_algorithm

def test_ga_converges_over_generations():
    """Fitness improves or stays same over generations.
    
    Hoare's Maxim: "Premature optimization is the root of all evil"
    → Profile first, optimize only if needed.
    """
    fitness_history = run_genetic_algorithm(generations=10)
    assert fitness_history[-1] <= fitness_history[0]


def test_fitness_uses_distance_matrix():
    """Verify O(1) lookup, not live A* calls.
    
    SOLID: Interface Segregation - fitness function depends only on
    distance matrix abstraction, not A* implementation.
    """
    # Mock distance matrix, verify no A* calls made
    #
```

### System Tests (`src/tests/test_system.py`)

```python
"""System tests: full pipeline execution."""
import pytest
import time
import os

def test_full_pipeline_execution_time():
    """End-to-end execution < 2 minutes.
    
    Performance requirement from checklist.
    """
    start = time.time()
    # ... run full pipeline ...
    elapsed = time.time() - start
    assert elapsed < 120  # 2 minutes


def test_output_files_exist():
    """Verify all output files created correctly."""
    assert os.path.exists("outputs/convergence_plot.png")
    assert os.path.exists("outputs/optimal_stations.json")
    #
```

### Performance Profiling

```python
"""Performance profiling hooks in run_genetic_algorithm.py."""
import cProfile
import pstats
from memory_profiler import profile

# Add @profile decorator to functions needing memory analysis
# Run: python -m memory_profiler run_genetic_algorithm.py

def profile_fitness_evaluation():
    """Profile fitness calculation hot path."""
    pr = cProfile.Profile()
    pr.enable()
    
    # ... run GA ...
    
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative').print(20)
    # Top 20 functions by cumulative time
```

**Profiling workflow:**
1. Run with `cProfile` to identify bottlenecks
2. If time > 2min: optimize fitness vectorization
3. Run with `memory_profiler` if memory > 500MB
4. Hoare's Maxim: optimize ONLY confirmed bottlenecks

---

## Disconnected Node Handling: Selected Approach

### Analysis of Options

| Approach | Time Complexity | Space | Complexity | Notes |
|----------|----------------|-------|------------|-------|
| A) Large penalty (10× max) | O(N) per fitness | O(1) | Low | Adds per-gen overhead |
| B) Filter unreachable nodes | O(N) filter each gen | O(N) mask | Low | Changes fitness landscape |
| C) Skip + assign inf | O(N) check | O(1) | Low | Simple but repeated checks |
| **D) Pre-compute mask at init** | **O(1) check per fitness** | **O(N)** | **Low** | **Lowest time cost** |

### Selected: Option D — Pre-compute Reachable Mask at Init

**Rationale:**
- **Time:** O(1) boolean array lookup in hot loop (fitness evaluation runs 50×100 = 5000 times)
- **Space:** ~50 bytes for Model Town (50-node boolean array)
- **KISS:** Simple bitmask, no complex logic in critical path
- **YAGNI:** Don't add complexity until profiling proves it's needed

### Implementation

```python
import numpy as np

def compute_reachable_mask(distance_matrix: np.ndarray) -> np.ndarray:
    """Compute boolean mask of reachable nodes.
    
    A node is reachable if it can be reached from OR can reach
    at least one other node in the graph.
    
    Args:
        distance_matrix: (N, N) matrix from distance_matrix.npy
        
    Returns:
        Boolean mask where True = node is reachable
    """
    # Nodes that can be reached from at least one other node
    row_reachable = ~np.isinf(distance_matrix).all(axis=1)
    col_reachable = ~np.isinf(distance_matrix).all(axis=0)
    return row_reachable & col_reachable


def calculate_fitness(
    genome: list[int],
    distance_matrix: np.ndarray,
    node_index: dict,
    reachable_mask: np.ndarray
) -> float:
    """Calculate fitness: sum of distances to nearest base.
    
    Uses vectorized numpy operations for O(N) instead of O(N×B).
    Only considers reachable nodes in fitness calculation.
    
    Args:
        genome: List of 5 node IDs (ambulance bases)
        distance_matrix: Precomputed (N, N) distance matrix
        node_index: Mapping from node ID to matrix index
        reachable_mask: Precomputed boolean mask
        
    Returns:
        Fitness score (lower = better for minimization)
    """
    # Convert genome to indices once
    base_indices = np.array([node_index[n] for n in genome])
    
    # Get reachable node indices
    reachable_indices = np.where(reachable_mask)[0]
    
    # Vectorized: distances from all nodes to all bases
    # Shape: (num_reachable_nodes, num_bases)
    distances = distance_matrix[reachable_indices][:, base_indices]
    
    # Nearest base for each reachable node
    min_distances = np.min(distances, axis=1)
    
    # Handle any remaining inf (shouldn't happen with good mask)
    min_distances = np.where(np.isinf(min_distances), 0, min_distances)
    
    return float(np.sum(min_distances))
```

**Performance optimizations applied:**
- Single array conversion for genome → indices
- `np.where(reachable_mask)[0]` — O(N) once, not per-call
- Vectorized `min(axis=1)` — O(N×B) → O(N) with numpy
- No Python loops in fitness hot path
- Local variable caching (`num_bases`, `base_indices`)

---

## Architecture (SOLID-compliant)

```
src/
├── genetic_algorithm.py     # Single Responsibility: GA logic
│   └── GeneticAlgorithm   # Open/Closed: extendable operators
├── fitness.py              # Single Responsibility: fitness calc
│   └── calculate_fitness   # Pure function, no side effects
├── run_genetic_algorithm.py # Facade: orchestrates pipeline
│   └── main()              # Entry point
└── tests/
    ├── test_genetic_algorithm.py  # Unit tests
    ├── test_integration.py       # Integration tests
    └── test_system.py            # System/performance tests
```

**SOLID principles applied:**
- **S**ingle Responsibility: Each module has one reason to change
- **O**pen/Closed: GA operators extendable without modification
- **L**iskov Substitution: Fitness function contract is clear
- **I**nterface Segregation: Minimal dependencies (distance_matrix only)
- **D**ependency Inversion: Depends on abstractions (matrix), not concretions

---

## Next Steps

1. Create test files first (TDD approach)
2. Implement GA framework (US-009)
3. Implement fitness function with reachable mask (US-010)
4. Add convergence tracking (US-011)
5. Add visualization (US-012)
6. Profile and optimize if needed

---

**Next:** Sprint 4 — Simulation Engine & Ambulance Agents