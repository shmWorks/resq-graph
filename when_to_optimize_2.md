- For the **ResQ-Graph** project, your performance effort should be focused on the intersection of **Simulation Fidelity** and **Search Efficiency**. Because this is an agent-based model (ABM) optimizing life-critical response times, your "Point of Diminishing Returns" is defined by the **Statistical Confidence** of your results.

### 🚑 ResQ-Graph Performance Heuristics

##### 1. The "Simulation Significance" Threshold

In a stochastic simulation like ResQ-Graph (Poisson spawners, random fleet placement), a single run is noise. You need batch runs to find the true mean response time.

- **Worth the effort**: Optimizing the `simulation_engine.py` or `headless` runner to be 2x faster. This directly allows you to run 2x more Monte Carlo trials in the same time, narrowing your confidence intervals.
- **Diminishing Return**: Optimizing the Pygame renderer beyond 60 FPS. Once the visual flow is smooth, additional GPU/CPU cycles spent on rendering provide zero value to the optimization research.

#### 2. Pathfinding: A\* vs. Distance Matrix

You already use a `distance_matrix.npy` for $O(1)$ dispatch lookups. This was a high-value optimization.

- **Worth the effort**: Dynamic caching of A\* paths for frequently traversed "trunk" roads. If 50 ambulances all take the same highway, recalculating the same nodes is a waste.
- **Diminishing Return**: Implementing a more complex heuristic than Haversine for A\* if the city grid is relatively standard. The compute cost of a "smarter" heuristic often outweighs the few nodes it saves in the open set.

#### 3. The Memetic Algorithm (GA + Local Search)

Your `src/genetic_algorithm.py` uses "Stochastic Hill Climbing" (`_local_search`) on 10% of children.

- **The "Worth It" Zone**: The **Greedy Seeding** you implemented. Starting the GA with a Medoid-based guess ($O(K \cdot N)$) is infinitely more valuable than running 1000 more random generations.
- **The Diminishing Return**: Increasing `tournament_size` or `population_size` indefinitely. Beyond a certain point, the diversity of the gene pool saturates, and you are just burning ALU cycles for "converging" on the same local optima.

---

### 🧠 Specific "Stop Points" for ResQ-Graph

I have identified three specific scenarios where you should stop optimizing:

| Component              | Strategy              | When to STOP                                                                                                                                                                 |
| :--------------------- | :-------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HDBSCAN Clustering** | Proactive Rebalancing | When the time to compute clusters exceeds 1 simulation "tick." Rebalancing must be faster than the movement it triggers.                                                     |
| **Traffic Model**      | Edge Weighting        | When edge weight updates take >5% of the total tick time. Traffic is an approximation; 99% accuracy isn't worth a 50% slower simulation.                                     |
| **Fitness Function**   | Response Time Calc    | When you've vectorized the math via NumPy. Moving from Python `for` loops to NumPy is worth 100x; moving from NumPy to Cython for a 5% gain is usually a diminishing return. |

### 🛠 Actionable Strategy: "The 10-Simulation Test"

If you are considering a performance tweak:

1. Run 10 headless simulations with a fixed seed and time them.
2. Implement the tweak.
3. If the total time doesn't drop by at least **5%**, revert the change. The added **Complexity Tax** (lines of code to maintain) is higher than the performance benefit.

### 🧠 Project Wisdom Update (Internalized)

> [!TIP]
> **SIMD-Vectorization** is your best friend for `fitness.py`. Since you are already using `distance_matrix.npy`, ensure all dispatch logic uses `np.argmin` across the entire ambulance vector rather than iterating. This is the "terminal state" of performance for this project.

_No files were modified. These insights are tailored to the `src/` architecture and current Sprint 8 status._
