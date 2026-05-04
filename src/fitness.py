"""Fitness function for facility location optimization.

Uses precomputed distance matrix for O(1) lookups.
"""
import numpy as np
from typing import List, Dict, Tuple


DUPLICATE_PENALTY = 1000.0


def compute_reachable_mask(distance_matrix: np.ndarray) -> np.ndarray:
    """Compute boolean mask of reachable nodes.

    A node is reachable if it can be reached from OR can reach
    at least one other node in the graph.

    Args:
        distance_matrix: (N, N) distance matrix.

    Returns:
        Boolean mask where True = node is reachable.
    """
    row_reachable = ~np.isinf(distance_matrix).all(axis=1)
    col_reachable = ~np.isinf(distance_matrix).all(axis=0)
    return row_reachable & col_reachable


def create_node_index(nodes: List) -> Dict:
    """Create mapping from node ID to matrix index.

    Args:
        nodes: List of node IDs.

    Returns:
        Dict mapping node ID to index.
    """
    return {node: i for i, node in enumerate(nodes)}


def calculate_fitness(
    genome: List[int],
    distance_matrix: np.ndarray,
    node_index: Dict,
    reachable_mask: np.ndarray,
    duplicate_penalty: float = DUPLICATE_PENALTY,
) -> float:
    """Calculate fitness: sum of distances to nearest base.

    Vectorized implementation for performance.

    Args:
        genome: List of node IDs (ambulance bases).
        distance_matrix: Precomputed (N, N) distance matrix.
        node_index: Mapping from node ID to matrix index.
        reachable_mask: Precomputed boolean mask of reachable nodes.
        duplicate_penalty: Penalty for duplicate bases.

    Returns:
        Fitness score (lower = better).
    """
    # Convert genome to indices once
    base_indices = np.array([node_index[n] for n in genome])

    # Check duplicates
    unique_bases = len(set(genome))
    duplicate_count = len(genome) - unique_bases
    duplicate_penalty_total = duplicate_count * duplicate_penalty

    # Get reachable node indices
    reachable_indices = reachable_mask.nonzero()[0]

    # Vectorized: distances from all reachable nodes to all bases
    # Shape: (num_reachable_nodes, num_bases)
    distances = distance_matrix[reachable_indices[:, np.newaxis], base_indices]

    # Nearest base for each reachable node
    min_distances = np.min(distances, axis=1)

    # Handle any remaining inf
    min_distances = np.where(np.isinf(min_distances), 0, min_distances)

    return float(np.sum(min_distances)) + duplicate_penalty_total


class FitnessFunction:
    """Fitness function with cached state.

    Optimizes by pre-computing index arrays.
    """

    def __init__(
        self,
        distance_matrix: np.ndarray,
        nodes: List,
        reachable_mask: np.ndarray,
    ):
        """Initialize with pre-computed data.

        Args:
            distance_matrix: Precomputed distance matrix.
            nodes: List of node IDs.
            reachable_mask: Precomputed reachable mask.
        """
        self.distance_matrix = distance_matrix
        self.nodes = nodes
        self.node_index = create_node_index(nodes)
        self.reachable_mask = reachable_mask
        self.reachable_indices = reachable_mask.nonzero()[0]

        # Pre-compute base index array for fast lookup
        self._base_indices = None

    def __call__(self, genome: List[int]) -> float:
        """Evaluate fitness of genome.

        Args:
            genome: List of node IDs.

        Returns:
            Fitness score.
        """
        return calculate_fitness(
            genome,
            self.distance_matrix,
            self.node_index,
            self.reachable_mask,
        )


def load_fitness_function(
    distance_matrix_path: str = "data/distance_matrix.npy",
    nodes: List = None,
) -> FitnessFunction:
    """Load fitness function with data.

    Args:
        distance_matrix_path: Path to distance matrix.
        nodes: List of node IDs. If None, load from graphml.

    Returns:
        FitnessFunction instance.
    """
    import networkx as nx

    distance_matrix = np.load(distance_matrix_path)

    if nodes is None:
        G = nx.read_graphml("data/model_town.graphml")
        nodes = list(G.nodes())

    reachable_mask = compute_reachable_mask(distance_matrix)

    return FitnessFunction(distance_matrix, nodes, reachable_mask)