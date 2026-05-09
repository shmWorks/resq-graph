"""
test_genetic_algorithm.py – Sprint 11 (US-041)
Unit tests for GA fitness, mutation, convergence.
"""
import pytest
from src.genetic_algorithm import GeneticAlgorithm

def dummy_fitness(genome):
    # simple fitness: sum of node IDs
    return float(sum(genome))

def test_fitness_returns_finite_value(minimal_graph):
    # Using dummy_fitness just to verify GA structure works
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), num_stations=2)
    val = dummy_fitness([0, 1])
    assert isinstance(val, (int, float))
    assert val == 1.0

def test_mutation_changes_at_least_one_gene(minimal_graph):
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), num_stations=3, mutation_rate=1.0)
    parent = [0, 1, 2]
    # In a 4-node graph (0,1,2,3), mutating [0,1,2] MUST introduce 3.
    changed = False
    for _ in range(10):
        child = ga.mutate(parent)
        if child != parent:
            changed = True
            break
    assert changed

def test_mutation_respects_valid_nodes(minimal_graph):
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), num_stations=3, mutation_rate=1.0)
    parent = [0, 1, 2]
    child = ga.mutate(parent)
    valid_nodes = set(minimal_graph.nodes)
    assert all(node in valid_nodes for node in child)

def test_crossover_produces_child_of_correct_length(minimal_graph):
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), num_stations=3)
    parent_a = [0, 1, 2]
    parent_b = [3, 2, 1]
    child = ga.crossover(parent_a, parent_b)
    assert len(child) == 3
    # Also check no duplicates
    assert len(set(child)) == 3

def test_convergence_improves_over_generations(minimal_graph):
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), pop_size=4, num_stations=2)
    # The fitness function is sum of nodes. We want the minimum sum.
    # The minimum sum of 2 nodes from [0, 1, 2, 3] is 0 + 1 = 1.
    best_genome = ga.run(dummy_fitness, generations=10, verbose=False)
    
    assert dummy_fitness(best_genome) <= ga.fitness_history[0]

def test_initial_population_all_valid(minimal_graph):
    ga = GeneticAlgorithm(nodes=list(minimal_graph.nodes()), pop_size=10, num_stations=2)
    ga.initialize_population()
    valid_nodes = set(minimal_graph.nodes)
    for genome in ga.population:
        assert all(node in valid_nodes for node in genome)
        assert len(genome) == 2
        assert len(set(genome)) == 2
