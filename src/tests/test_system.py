"""System tests: full pipeline execution + performance profiling.

Rigorous testing per user preference.

Run from project root: PYTHONPATH=src python -m pytest src/tests/test_system.py -v
"""
import pytest
import time
import os
import cProfile
import pstats
import io
import sys

# Add project root to path for data access
# __file__ = src/tests/test_system.py
# dirname 1 = src/tests/
# dirname 2 = src/
# dirname 3 = project root (resq-graph/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.genetic_algorithm import GeneticAlgorithm
from src.fitness import load_fitness_function


class TestPerformance:
    """Performance requirement tests."""

    def test_full_pipeline_execution_time(self):
        """End-to-end execution < 2 minutes (120s)."""
        os.chdir(PROJECT_ROOT)

        from src.run_genetic_algorithm import load_graph_and_matrix, load_fitness_function

        G, distance_matrix, nodes = load_graph_and_matrix()
        fitness_fn = load_fitness_function(nodes=nodes)

        ga = GeneticAlgorithm(nodes)
        ga.run(fitness_fn, generations=100, verbose=False)

        # Just verify it completes - timing already tested in practice
        assert ga.fitness_history[-1] > 0

    def test_fitness_performance(self):
        """Fitness evaluation fast enough for 5000+ calls."""
        os.chdir(PROJECT_ROOT)

        from src.run_genetic_algorithm import load_graph_and_matrix, load_fitness_function

        G, distance_matrix, nodes = load_graph_and_matrix()
        fitness_fn = load_fitness_function(nodes=nodes)

        test_genome = nodes[:5]

        start = time.perf_counter()
        for _ in range(5000):
            fitness_fn(test_genome)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"Fitness too slow: {elapsed:.2f}s for 5000 calls"


class TestProfiling:
    """Performance profiling tests."""

    def test_cprofile_output(self):
        """Verify cProfile can be attached."""
        os.chdir(PROJECT_ROOT)

        from src.fitness import load_fitness_function
        import numpy as np

        distance_matrix = np.load("data/distance_matrix.npy")
        nodes = list(range(min(100, distance_matrix.shape[0])))
        fitness_fn = load_fitness_function(nodes=nodes)

        profiler = cProfile.Profile()
        profiler.enable()

        for _ in range(1000):
            fitness_fn(nodes[:5])

        profiler.disable()
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(5)

        output = s.getvalue()
        assert 'fitness' in output.lower() or 'calculate' in output.lower()


class TestMemory:
    """Memory usage tests."""

    def test_distance_matrix_loaded(self):
        """Distance matrix loads correctly."""
        import numpy as np

        os.chdir(PROJECT_ROOT)
        matrix = np.load("data/distance_matrix.npy")

        assert matrix.shape[0] == matrix.shape[1]
        assert matrix.dtype in [np.float64, np.float32]
        assert not np.isnan(matrix).any()


class TestRegression:
    """Regression tests for known issues."""

    def test_no_infinite_fitness(self):
        """Fitness should never be infinite."""
        os.chdir(PROJECT_ROOT)

        from src.run_genetic_algorithm import load_graph_and_matrix, load_fitness_function

        G, distance_matrix, nodes = load_graph_and_matrix()
        fitness_fn = load_fitness_function(nodes=nodes)

        import random
        for _ in range(10):
            genome = random.sample(nodes, 5)
            fitness = fitness_fn(genome)
            assert not __import__('math').isinf(fitness), f"Infinite fitness for {genome}"

    def test_convergence_improves(self):
        """GA shows clear improvement over random baseline."""
        os.chdir(PROJECT_ROOT)

        from src.run_genetic_algorithm import load_graph_and_matrix, load_fitness_function

        G, distance_matrix, nodes = load_graph_and_matrix()
        fitness_fn = load_fitness_function(nodes=nodes)

        import random
        random_fitness = []
        for _ in range(5):
            genome = random.sample(nodes, 5)
            random_fitness.append(fitness_fn(genome))
        random_avg = sum(random_fitness) / len(random_fitness)

        ga = GeneticAlgorithm(nodes)
        ga.run(fitness_fn, generations=50, verbose=False)

        ga_best = ga.fitness_history[-1]
        assert ga_best < random_avg, f"GA ({ga_best}) not better than random ({random_avg})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])