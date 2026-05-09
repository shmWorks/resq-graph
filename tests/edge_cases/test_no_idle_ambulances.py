"""
test_no_idle_ambulances.py – Sprint 11 (US-043)
Edge case: events spawn but all ambulances are busy.
"""
import pytest
import numpy as np
from src.simulation.simulation_engine import SimulationEngine
from src.simulation.event_spawner import Accident

def test_events_queue_when_ambulances_busy(minimal_graph):
    nodes = list(minimal_graph.nodes())
    node_positions = {n: (0,0) for n in nodes}
    distance_matrix = np.zeros((4,4))
    start_nodes = [0] # 1 ambulance
    
    engine = SimulationEngine(
        graph=minimal_graph,
        node_positions=node_positions,
        distance_matrix=distance_matrix,
        start_nodes=start_nodes,
        ticks=10,
        headless=True
    )
    
    # Manually make the single ambulance busy
    engine.ambulances[0].state = "ON_SCENE"
    
    # Dispatch an event
    event = Accident(id=1, timestamp=1, location=1, pixel_pos=(0,0), priority=1)
    engine.dispatcher.tick([event], current_tick=1)
    
    # Event should remain active and unassigned
    assert len(engine.dispatcher.active_events) == 1
    assert engine.dispatcher.active_events[0].assigned_ambulance_id is None
    assert event.id not in engine.dispatcher.assigned_events
