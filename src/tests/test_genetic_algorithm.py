"""Unit tests for GA operators.

Rigorous testing per user preference.
"""
import pytest
import random
import numpy as np
from genetic_algorithm import GeneticAlgorithm, NUM_STATIONS


class TestGenomeRepresentation:
    """Genome structure validation."""

    def test_no_duplicate_nodes(self):
        """Genome must not contain duplicate node IDs."""
        nodes = list(range(100))
        ga = GeneticAlgorithm(nodes)
        ga.initialize_population()

        for genome in ga.population:
            assert len(genome) == len(set(genome)), \
                f"Duplicate nodes found: {genome}"

    def test_length_equals_num_stations(self):
        """Genome length must match NUM_STATIONS."""
        nodes = list(range(100))
        ga = GeneticAlgorithm(nodes)
        ga.initialize_population()

        for genome in ga.population:
            assert len(genome) == NUM_STATIONS, \
                f"Expected {NUM_STATIONS}, got {len(genome)}"

    def test_nodes_in_valid_range(self):
        """All nodes must exist in graph."""
        nodes = list(range(100))
        ga = GeneticAlgorithm(nodes)
        ga.initialize_population()

        node_set = set(nodes)
        for genome in ga.population:
            for node in genome:
                assert node in node_set, \
                    f"Invalid node {node} not in graph"


class TestSelection:
    """Selection operator tests."""

    def test_roulette_wheel_returns_valid_genome(self):
        """Selection must return valid genome from population."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes, pop_size=10)
        ga.initialize_population()

        # All same fitness - should still return valid genome
        fitnesses = [1.0] * 10

        selected = ga.select_parents(fitnesses)
        assert isinstance(selected, list)
        assert len(selected) == NUM_STATIONS

    def test_selection_respects_fitness(self):
        """Higher fitness (lower value) = more likely selected."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes, pop_size=10)
        ga.initialize_population()

        # Set explicit fitnesses
        # Index 0 has best fitness (lowest), should be selected more
        fitnesses = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        # Run many selections
        counts = {i: 0 for i in range(10)}
        for _ in range(1000):
            selected = ga.select_parents(fitnesses)
            idx = ga.population.index(selected)
            counts[idx] += 1

        # Best genome (index 0) should be selected more than worst (index 9)
        assert counts[0] > counts[9], \
            f"Selection not respecting fitness: {counts}"


class TestCrossover:
    """Crossover operator tests."""

    def test_offspring_has_valid_length(self):
        """Offspring length equals parent length."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        parent_a = [1, 2, 3, 4, 5]
        parent_b = [6, 7, 8, 9, 10]

        child = ga.crossover(parent_a, parent_b)
        assert len(child) == NUM_STATIONS

    def test_no_duplicate_nodes_in_offspring(self):
        """Crossover must not create duplicates."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        # Parents with overlap at crossover point
        parent_a = [1, 2, 3, 4, 5]
        parent_b = [3, 7, 8, 9, 10]  # 3 is duplicate

        child = ga.crossover(parent_a, parent_b)
        assert len(child) == len(set(child)), \
            f"Duplicates in offspring: {child}"


class TestMutation:
    """Mutation operator tests."""

    def test_mutated_genome_stays_in_bounds(self):
        """Mutated node ID must exist in graph."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes, mutation_rate=1.0)

        genome = [1, 2, 3, 4, 5]

        # Run multiple times to ensure mutation happens
        for _ in range(20):
            mutated = ga.mutate(genome.copy())
            for node in mutated:
                assert node in nodes, f"Invalid node {node}"

    def test_mutation_rate_respected(self):
        """With rate=0, genome unchanged. With rate=1, always changes."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        genome = [1, 2, 3, 4, 5]

        # Rate = 0: always same
        ga_no_mut = GeneticAlgorithm(nodes, mutation_rate=0.0)
        for _ in range(10):
            mutated = ga_no_mut.mutate(genome.copy())
            assert mutated == genome, "Mutation rate 0 should not mutate"

        # Rate = 1: at least one position changes
        ga_full_mut = GeneticAlgorithm(nodes, mutation_rate=1.0)
        changed_count = 0
        for _ in range(20):
            mutated = ga_full_mut.mutate(genome.copy())
            if mutated != genome:
                changed_count += 1

        assert changed_count > 0, "Mutation rate 1 should mutate"


class TestFixDuplicates:
    """Duplicate fixing logic."""

    def test_empty_list(self):
        """Empty genome handled gracefully."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        result = ga._fix_duplicates([])
        assert len(result) <= NUM_STATIONS

    def test_all_duplicates(self):
        """All same nodes → filled with randoms."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        result = ga._fix_duplicates([1, 1, 1, 1, 1])
        assert len(result) == NUM_STATIONS
        assert len(set(result)) == NUM_STATIONS


class TestEdgeCases:
    """Edge case handling."""

    def test_small_graph(self):
        """GA works with minimum nodes."""
        nodes = list(range(5))  # Exactly 5 nodes
        ga = GeneticAlgorithm(nodes, pop_size=10)
        ga.initialize_population()

        assert len(ga.population) == 10

    def test_fitness_history_tracked(self):
        """Fitness history recorded per generation."""
        nodes = list(range(20))
        ga = GeneticAlgorithm(nodes)

        def dummy_fitness(g):
            return float(sum(g))

        ga.run(dummy_fitness, generations=10, verbose=False)

        assert len(ga.fitness_history) == 10
        # Should improve or stay same (monotonic or equal)
        for i in range(1, len(ga.fitness_history)):
            assert ga.fitness_history[i] <= ga.fitness_history[i-1] * 1.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])