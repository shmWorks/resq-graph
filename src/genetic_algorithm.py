"""Genetic Algorithm for facility location optimization.

Implements evolutionary algorithm to find optimal ambulance base station positions.
"""
import random
import numpy as np
from typing import List, Callable, Optional


NUM_STATIONS = 5
POPULATION_SIZE = 50
MUTATION_RATE = 0.1
GENERATIONS = 100


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
        self, fitnesses: List[float]
    ) -> List[int]:
        """Roulette wheel selection.

        Args:
            fitnesses: List of fitness values (lower = better).

        Returns:
            Selected genome.
        """
        # Convert to maximization (higher = better)
        max_fitness = max(fitnesses)
        inverted = [max_fitness - f for f in fitnesses]

        total = sum(inverted)
        if total == 0:
            return random.choice(self.population)

        # Roulette wheel
        pick = random.uniform(0, total)
        cumulative = 0.0
        for i, fitness in enumerate(inverted):
            cumulative += fitness
            if cumulative >= pick:
                return self.population[i].copy()

        return self.population[-1].copy()

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

    def run(
        self,
        fitness_fn: Callable[[List[int]], float],
        generations: int = GENERATIONS,
        verbose: bool = True,
    ) -> List[int]:
        """Run GA evolution.

        Args:
            fitness_fn: Function that takes genome returns fitness.
            generations: Number of generations to run.
            verbose: Print progress.

        Returns:
            Best genome found.
        """
        self.initialize_population()

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