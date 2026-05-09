"""Genetic Algorithm for facility location optimization.

Implements evolutionary algorithm to find optimal ambulance base station positions.
"""
import random
import numpy as np
from typing import List, Callable, Optional


NUM_STATIONS = 5
POPULATION_SIZE = 100
MUTATION_RATE = 0.2
GENERATIONS = 150


class GeneticAlgorithm:
    """GA for evolving base station locations.

    Attributes:
        nodes: List of valid node IDs in the graph.
        population: Current population of genomes.
        fitness_history: Best fitness per generation.
    """

    def __init__(
        self,
        nodes: List,
        pop_size: int = POPULATION_SIZE,
        num_stations: int = NUM_STATIONS,
        mutation_rate: float = MUTATION_RATE,
    ):
        """Initialize GA.

        Args:
            nodes: Valid node IDs from graph.
            pop_size: Population size (default 50).
            num_stations: Number of base stations (default 5).
            mutation_rate: Probability of mutation (default 0.1).
        """
        self.nodes = nodes
        self.num_nodes = len(nodes)
        self.pop_size = pop_size
        self.num_stations = num_stations
        self.mutation_rate = mutation_rate
        self.population: List[List[int]] = []
        self.fitness_history: List[float] = []

        self._node_set = set(nodes)

    def initialize_population(self) -> None:
        """Create initial population with random genomes.

        Each genome: list of NUM_STATIONS unique node IDs.
        """
        self.population = []
        for _ in range(self.pop_size):
            genome = self._random_genome()
            self.population.append(genome)

    def _random_genome(self) -> List[int]:
        """Generate random genome with no duplicates."""
        return random.sample(self.nodes, self.num_stations)

    def select_parents(
        self, fitnesses: List[float], tournament_size: int = 3
    ) -> List[int]:
        """Tournament selection.

        Args:
            fitnesses: List of fitness values (lower = better).
            tournament_size: Number of individuals to compare.

        Returns:
            Selected genome.
        """
        # Pick random candidates
        indices = random.sample(range(len(self.population)), tournament_size)
        
        # Return the best one (lowest fitness)
        best_idx = indices[0]
        for idx in indices[1:]:
            if fitnesses[idx] < fitnesses[best_idx]:
                best_idx = idx
        
        return self.population[best_idx].copy()

    def crossover(
        self, parent_a: List[int], parent_b: List[int]
    ) -> List[int]:
        """Single-point crossover.

        Args:
            parent_a: First parent genome.
            parent_b: Second parent genome.

        Returns:
            Child genome.
        """
        if len(parent_a) != len(parent_b):
            raise ValueError("Parents must have same length")

        point = random.randint(1, len(parent_a) - 1)

        # Combine and fix duplicates
        combined = parent_a[:point] + parent_b[point:]
        return self._fix_duplicates(combined)

    def _fix_duplicates(self, genome: List[int]) -> List[int]:
        """Replace duplicate nodes with random unique nodes.

        Args:
            genome: Genome with potential duplicates.

        Returns:
            Genome with no duplicates.
        """
        seen = set()
        result = []
        for node in genome:
            if node not in seen:
                seen.add(node)
                result.append(node)

        # Fill remaining slots with random nodes
        while len(result) < self.num_stations:
            available = [n for n in self.nodes if n not in seen]
            if not available:
                break
            node = random.choice(available)
            seen.add(node)
            result.append(node)

        return result

    def mutate(self, genome: List[int]) -> List[int]:
        """Random node swap mutation.

        Args:
            genome: Genome to mutate.

        Returns:
            Mutated genome (may be same if no mutation occurs).
        """
        if random.random() > self.mutation_rate:
            return genome.copy()

        # Swap one position with random node
        result = genome.copy()
        pos = random.randint(0, self.num_stations - 1)

        available = [n for n in self.nodes if n not in result]
        if available:
            result[pos] = random.choice(available)

        return result

    def _greedy_genome(self, distance_matrix: np.ndarray) -> List[int]:
        """Construct a high-quality genome greedily in O(K*N).
        
        Args:
            distance_matrix: (N, N) distance matrix.
            
        Returns:
            A high-quality initial genome.
        """
        num_nodes = distance_matrix.shape[0]
        # Start with the node that has the minimum total distance to all others (Medoid)
        current_best_distances = np.full(num_nodes, np.inf)
        selected_indices = []
        
        # Only consider reachable nodes from the mask if possible, 
        # but for simplicity we'll use the whole matrix as it's pre-filtered.
        
        for _ in range(self.num_stations):
            # For every node, calculate what the total distance would be if we added it
            # total_dist(j) = sum(min(current_best_distances, dist_to_j))
            potential_distances = np.minimum(current_best_distances[:, np.newaxis], distance_matrix)
            total_potential_costs = np.sum(potential_distances, axis=0)
            
            # Avoid picking the same node twice
            for idx in selected_indices:
                total_potential_costs[idx] = np.inf
                
            best_node_idx = np.argmin(total_potential_costs)
            selected_indices.append(best_node_idx)
            current_best_distances = potential_distances[:, best_node_idx]
            
        return [self.nodes[i] for i in selected_indices]

    def _local_search(self, genome: List[int], fitness_fn: Callable) -> List[int]:
        """Hill climbing: try swapping each station with its neighbors or random nodes."""
        best_genome = genome.copy()
        best_fitness = fitness_fn(best_genome)
        
        improved = True
        while improved:
            improved = False
            for i in range(len(best_genome)):
                original_node = best_genome[i]
                # Try a few random nodes to swap with (Stochastic Hill Climbing)
                # In a graph, we'd try neighbors, but random works for facility location.
                sample_size = min(10, len(self.nodes))
                candidates = random.sample(self.nodes, sample_size) 
                for candidate in candidates:
                    if candidate in best_genome: continue
                    
                    best_genome[i] = candidate
                    new_fitness = fitness_fn(best_genome)
                    
                    if new_fitness < best_fitness:
                        best_fitness = new_fitness
                        improved = True
                        break # Found a better node for this slot
                    else:
                        best_genome[i] = original_node # Revert
                if improved: break
        return best_genome

    def run(
        self,
        fitness_fn: Callable,
        generations: int = GENERATIONS,
        verbose: bool = True,
    ) -> List[int]:
        """Run GA evolution with Greedy Seeding and Local Search."""
        self.initialize_population()
        
        # --- ONE CHANGE: GREEDY SEEDING ---
        # If the fitness_fn is an instance of FitnessFunction, we can use its matrix
        if hasattr(fitness_fn, 'distance_matrix'):
            greedy_individual = self._greedy_genome(fitness_fn.distance_matrix)
            self.population[0] = greedy_individual
            if verbose: print("Greedy seed injected into population.")
        # ----------------------------------

        best_genome = None
        best_fitness = float('inf')

        for gen in range(generations):
            # Evaluate fitness
            fitnesses = [fitness_fn(g) for g in self.population]

            # Track best
            gen_best_idx = np.argmin(fitnesses)
            gen_best_fitness = fitnesses[gen_best_idx]
            self.fitness_history.append(gen_best_fitness)

            if gen_best_fitness < best_fitness:
                best_fitness = gen_best_fitness
                best_genome = self.population[gen_best_idx].copy()

            if verbose and gen % 10 == 0:
                print(f"Gen {gen}: best fitness = {gen_best_fitness:.2f}")

            # Create next generation
            new_population = []

            # Elitism: keep best
            new_population.append(self.population[gen_best_idx].copy())

            while len(new_population) < self.pop_size:
                parent_a = self.select_parents(fitnesses)
                parent_b = self.select_parents(fitnesses)

                child = self.crossover(parent_a, parent_b)
                child = self.mutate(child)
                
                # Periodically apply Local Search to children (Memetic Algorithm)
                if random.random() < 0.10: # 10% of children get "smarter"
                    child = self._local_search(child, fitness_fn)

                new_population.append(child)

            self.population = new_population

        return best_genome


def run_genetic_algorithm(
    nodes: List,
    fitness_fn: Callable,
    generations: int = GENERATIONS,
) -> tuple:
    """Convenience function to run GA.

    Args:
        nodes: Valid node IDs.
        fitness_fn: Fitness function.
        generations: Number of generations.

    Returns:
        Tuple of (best_genome, fitness_history).
    """
    ga = GeneticAlgorithm(nodes)
    best = ga.run(fitness_fn, generations)
    return best, ga.fitness_history