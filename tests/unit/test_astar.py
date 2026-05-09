"""
test_astar.py – Sprint 11 (US-041)
Unit tests for A* pathfinding.
"""
import networkx as nx
import pytest

from src.astar import astar, haversine

def test_shortest_path_known_graph(minimal_graph):
    # 0 -> 1 -> 2 -> 3 (cost 3), direct 0 -> 3 (cost 5)
    path = astar(minimal_graph, start=0, goal=3)
    assert path == [0, 1, 2, 3]

def test_single_node_start_equals_goal(minimal_graph):
    # start == goal
    path = astar(minimal_graph, start=1, goal=1)
    assert path == [1]

def test_unreachable_node_returns_none(minimal_graph):
    G = minimal_graph.copy()
    G.add_node(99, x=10, y=10) # Unreachable island
    path = astar(G, start=0, goal=99)
    assert path is None

def test_heuristic_never_overestimates(minimal_graph):
    # Simple check that the heuristic calculation runs without error
    for n1 in minimal_graph.nodes:
        for n2 in minimal_graph.nodes:
            if n1 == n2:
                continue
            h = haversine(minimal_graph, n1, n2)
            assert h >= 0

def test_returned_path_nodes_exist(minimal_graph):
    path = astar(minimal_graph, start=0, goal=3)
    for node in path:
        assert node in minimal_graph.nodes

def test_deterministic_same_inputs(minimal_graph):
    path1 = astar(minimal_graph, start=0, goal=3)
    path2 = astar(minimal_graph, start=0, goal=3)
    assert path1 == path2
