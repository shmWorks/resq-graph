"""Run genetic algorithm for facility location optimization.

Entry point: python run_genetic_algorithm.py
"""
import json
import time
import os
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi

from genetic_algorithm import GeneticAlgorithm, run_genetic_algorithm
from fitness import load_fitness_function, create_node_index, compute_reachable_mask


OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_graph_and_matrix():
    """Load graph and distance matrix."""
    G = nx.read_graphml("data/model_town.graphml")

    # Ensure numeric coordinates
    for node in G.nodes:
        G.nodes[node]['x'] = float(G.nodes[node]['x'])
        G.nodes[node]['y'] = float(G.nodes[node]['y'])

    distance_matrix = np.load("data/distance_matrix.npy")
    nodes = list(G.nodes())

    return G, distance_matrix, nodes


def plot_convergence(fitness_history, save_path=None):
    """Plot convergence: generation vs best fitness."""
    plt.figure(figsize=(10, 6))
    plt.plot(fitness_history, 'b-', linewidth=2)
    plt.xlabel('Generation')
    plt.ylabel('Best Fitness')
    plt.title('GA Convergence: Best Fitness per Generation')
    plt.grid(True, alpha=0.3)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Convergence plot saved to {save_path}")
    plt.close()


def visualize_stations(
    G,
    optimal_nodes,
    save_path=None,
):
    """Visualize optimal stations on map.

    Args:
        G: NetworkX graph.
        optimal_nodes: List of optimal node IDs.
        save_path: Path to save PNG.
    """
    # Get positions
    pos = {n: (G.nodes[n]['x'], G.nodes[n]['y']) for n in G.nodes()}

    # Random baseline for comparison
    nodes_list = list(G.nodes())
    np.random.seed(42)
    random_nodes = list(np.random.choice(nodes_list, 5, replace=False))

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))

    # Plot street network
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color='lightgray',
        width=0.5,
        alpha=0.7
    )

    # Random stations (gray)
    random_x = [pos[n][0] for n in random_nodes]
    random_y = [pos[n][1] for n in random_nodes]
    ax.scatter(random_x, random_y, c='gray', s=150, marker='o',
               label='Random Placement', zorder=3, alpha=0.6)

    # Optimal stations (blue stars)
    optimal_x = [pos[n][0] for n in optimal_nodes]
    optimal_y = [pos[n][1] for n in optimal_nodes]
    ax.scatter(optimal_x, optimal_y, c='blue', s=300, marker='*',
               label='Optimal (GA)', zorder=4, edgecolors='white', linewidths=1)

    ax.legend(loc='upper right', fontsize=10)
    ax.set_title('Optimal Ambulance Base Stations')
    ax.axis('off')

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Station visualization saved to {save_path}")
    plt.close()


def main():
    """Run full GA pipeline."""
    print("Loading data...")
    G, distance_matrix, nodes = load_graph_and_matrix()

    print(f"Graph: {len(nodes)} nodes, {G.number_of_edges()} edges")
    print(f"Distance matrix: {distance_matrix.shape}")

    # Compute reachable mask
    reachable_mask = compute_reachable_mask(distance_matrix)
    reachable_count = reachable_mask.sum()
    print(f"Reachable nodes: {reachable_count}/{len(nodes)}")

    # Load fitness function
    print("\nInitializing fitness function...")
    fitness_fn = load_fitness_function(nodes=nodes)

    # Run GA
    print(f"\nRunning GA (100 generations, pop=50)...")
    start_time = time.time()

    ga = GeneticAlgorithm(nodes)
    best_genome = ga.run(fitness_fn, generations=100, verbose=True)

    elapsed = time.time() - start_time
    print(f"\nExecution time: {elapsed:.2f}s")

    # Export results
    print("\nExporting results...")

    # Save optimal stations as JSON
    result = {
        "optimal_stations": best_genome,
        "best_fitness": ga.fitness_history[-1],
        "generations": 100,
        "execution_time_seconds": elapsed,
    }

    json_path = os.path.join(OUTPUT_DIR, "optimal_stations.json")
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to {json_path}")

    # Plot convergence
    conv_path = os.path.join(OUTPUT_DIR, "convergence_plot.png")
    plot_convergence(ga.fitness_history, save_path=conv_path)

    # Visualize stations
    viz_path = os.path.join(OUTPUT_DIR, "optimal_stations.png")
    visualize_stations(G, best_genome, save_path=viz_path)

    print(f"\nBest genome: {best_genome}")
    print(f"Best fitness: {ga.fitness_history[-1]:.2f}")

    return best_genome, ga.fitness_history


if __name__ == "__main__":
    main()