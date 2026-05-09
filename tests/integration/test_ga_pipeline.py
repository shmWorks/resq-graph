"""
test_ga_pipeline.py – Sprint 11 (US-042)
Integration test for the full GA -> Dispatcher -> Simulation pipeline.
"""
import pytest
from src.genetic_algorithm import run_genetic_algorithm
from src.simulation.simulation_engine import SimulationEngine

def dummy_fitness_for_integration(genome):
    return float(sum(genome))

def test_ga_to_simulation_pipeline(base_config, minimal_graph):
    # 1. Run GA to find optimal station placement
    nodes = list(minimal_graph.nodes())
    from src.genetic_algorithm import GeneticAlgorithm
    ga = GeneticAlgorithm(nodes=nodes, pop_size=4, num_stations=2)
    best_genome = ga.run(dummy_fitness_for_integration, generations=2, verbose=False)
    
    # 2. Assert GA returned valid locations
    assert best_genome is not None
    assert len(best_genome) == 2
    assert all(node in nodes for node in best_genome)
    
    # 3. Feed the genome to SimulationEngine
    import numpy as np
    distance_matrix = np.zeros((4, 4))
    node_positions = {n: (0,0) for n in nodes}
    
    engine = SimulationEngine(
        graph=minimal_graph, 
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=best_genome,
        ticks=10, 
        headless=True
    )
    
    # Verify initial placements match the GA output
    actual_start_nodes = [amb.current_path[0] if amb.current_path else amb.current_location for amb in engine.ambulances]
    # In SimulationEngine, if start_nodes is given, ambulances are placed there
    for i, amb in enumerate(engine.ambulances):
        assert amb.current_location == best_genome[i]
        
    # 4. Run the simulation
    engine.run()
    
    # Verify simulation completed and metrics were tracked
    assert engine.state.current_tick == 10
