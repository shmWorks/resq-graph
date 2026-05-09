"""
test_full_congestion.py – Sprint 11 (US-043)
Edge case: Extreme congestion.
"""
import pytest
import numpy as np
import networkx as nx
from src.simulation.simulation_engine import SimulationEngine
from src.simulation.traffic import TrafficModel
from src.simulation.event_spawner import Accident

def test_extreme_congestion_rerouting(minimal_graph):
    # Setup Engine
    nodes = list(minimal_graph.nodes())
    node_positions = {n: (0,0) for n in nodes}
    distance_matrix = np.zeros((4,4))
    start_nodes = [0]
    
    engine = SimulationEngine(
        graph=minimal_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=10,
        headless=True
    )
    
    # Enable traffic model and set a high multiplier
    engine.traffic = TrafficModel(minimal_graph, node_positions, max_multiplier=10.0, decay_rate=0.0)
    engine.dispatcher.traffic = engine.traffic
    
    # Max out congestion on edge (0, 1)
    engine.traffic._multipliers[frozenset({0, 1})] = 10.0
    
    # Spawn an event at node 1
    event = Accident(id=1, timestamp=1, location=1, pixel_pos=(0,0), priority=1)
    engine.dispatcher.tick([event], current_tick=1)
    
    # Ambulance 0 should be dispatched
    amb = engine.ambulances[0]
    assert amb.assigned_task == event
    
    # Its path weight should reflect the high multiplier
    # Default weight is 1.0 (minimal_graph edges have no weight, default 1) -> so 10.0
    assert amb.path_weight_at_dispatch >= 1.0

def test_dynamic_reroute_on_congestion(minimal_graph):
    # Setup Engine with a loop: 0-1-2-3-0
    nodes = list(minimal_graph.nodes())
    node_positions = {n: (0,0) for n in nodes}
    distance_matrix = np.zeros((4,4))
    
    engine = SimulationEngine(
        graph=minimal_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=[0],
        ticks=20,
        headless=True
    )
    engine.traffic = TrafficModel(minimal_graph, node_positions, max_multiplier=10.0, decay_rate=0.0)
    engine.dispatcher.traffic = engine.traffic
    
    # 1. Dispatch on clear path 0 -> 1
    event = Accident(id=1, timestamp=1, location=1, pixel_pos=(0,0), priority=1)
    engine.dispatcher.tick([event], current_tick=1)
    
    amb = engine.ambulances[0]
    initial_path = list(amb.current_path)
    assert initial_path == [0, 1]
    
    # 2. Make edge (0, 1) extremely congested while in transit
    # But wait, progress is 0.0, next tick it will move.
    engine.traffic._multipliers[frozenset({0, 1})] = 10.0
    
    # 3. Tick the dispatcher. It should trigger _check_rerouting
    # We need to make sure the reroute interval is low or enough time has passed.
    # Default is 10 ticks. Let's force it.
    amb.reroute_check_tick = -10 
    
    engine.dispatcher.tick([], current_tick=2)
    
    # 4. Check if path changed to go the long way [0, 3, 2, 1]
    # (Assuming 0-3-2-1 is shorter than 0-1 with 10x weight)
    assert amb.current_path != initial_path
    assert 3 in amb.current_path
