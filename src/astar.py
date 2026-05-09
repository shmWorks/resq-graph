import heapq
import math

# Module-level cache: node_id → (lat_radians, lon_radians)
# Populated lazily on first haversine call per node; shared across all A* calls.
_RAD_CACHE: dict = {}

def _get_radians(G, node):
    """Return (lat_rad, lon_rad) for node, caching the result."""
    if node not in _RAD_CACHE:
        _RAD_CACHE[node] = (
            math.radians(float(G.nodes[node]['y'])),
            math.radians(float(G.nodes[node]['x'])),
        )
    return _RAD_CACHE[node]


def haversine(G, u, v):
    phi1, lam1 = _get_radians(G, u)
    phi2, lam2 = _get_radians(G, v)
    R = 6371000
    dphi = phi2 - phi1
    dlambda = lam2 - lam1
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def astar(G, start, goal):
    """
    A* pathfinding algorithm.

    Parameters:
        G (networkx.Graph): Graph with 'x' (lon) and 'y' (lat) node attributes
        start (node): Start node ID
        goal (node): Goal node ID

    Returns:
        list: Ordered list of node IDs OR None if no path exists
    """
    if len(G.nodes) == 0:
        raise ValueError("Graph is empty.")
    if start == goal:
        return [start]
    if start not in G or goal not in G:
        return None

    open_set = []
    heapq.heappush(open_set, (0.0, start))

    came_from: dict = {}
    # Sparse dicts: only visited nodes stored (avoids O(N) pre-allocation)
    g_score: dict = {start: 0.0}
    closed: set = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        g_cur = g_score[current]
        for neighbor in G.neighbors(current):
            if neighbor in closed:
                continue
            edge_data = G[current][neighbor]
            weight = min(float(d.get('length', 1)) for d in edge_data.values())
            tentative_g = g_cur + weight

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + haversine(G, neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))

    return None