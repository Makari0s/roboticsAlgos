import math
import random

from shapely import Point
from shapely.geometry import Polygon


class QuadtreeCell:
    def __init__(self, bounds, depth=0, max_depth=5, min_size=20):
        self.bounds = bounds  # (x1, y1, x2, y2)
        self.depth = depth
        self.max_depth = max_depth
        self.min_size = min_size
        self.children = []
        self.is_obstructed = False
        self.is_subdivided = False

    def subdivide(self, obstacles):
        # Frühzeitiger Abbruch nur wenn nicht blockiert UND nicht bereits unterteilt
        if not self.is_obstructed or self.is_subdivided:
            return

        # Unterteilungsbedingungen überprüfen
        if self.depth < self.max_depth and self.size > self.min_size:
            # [Rest der Methode unverändert]

            x1, y1, x2, y2 = self.bounds
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            self.children = [
                QuadtreeCell((x1, y1, mid_x, mid_y), self.depth + 1, self.max_depth, self.min_size),
                QuadtreeCell((mid_x, y1, x2, mid_y), self.depth + 1, self.max_depth, self.min_size),
                QuadtreeCell((x1, mid_y, mid_x, y2), self.depth + 1, self.max_depth, self.min_size),
                QuadtreeCell((mid_x, mid_y, x2, y2), self.depth + 1, self.max_depth, self.min_size)
            ]

            self.is_subdivided = True  # Verhindert Mehrfachunterteilung

            for child in self.children:
                child.check_obstruction(obstacles)
                child.subdivide(obstacles)  # Rekursiv nur für blockierte Kinder

    def check_obstruction(self, obstacles):
        cell_poly = Polygon([
            (self.bounds[0], self.bounds[1]),
            (self.bounds[2], self.bounds[1]),
            (self.bounds[2], self.bounds[3]),
            (self.bounds[0], self.bounds[3])
        ])

        # Vereinfachte Bedingung
        self.is_obstructed = any(
            cell_poly.intersects(Polygon(obs))
            for obs in obstacles
        )

    @property
    def size(self):
        return self.bounds[2] - self.bounds[0]


def generate_random_polygon(width, height, max_radius, max_vertices):
    cx = random.uniform(max_radius, width - max_radius)
    cy = random.uniform(max_radius, height - max_radius)
    n = random.randint(3, max_vertices)
    angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(n)])
    base_radius = random.uniform(max_radius / 2, max_radius)
    vertices = []
    for angle in angles:
        r = base_radius * random.uniform(0.8, 1.2)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        vertices.append((x, y))
    convex_vertices = Polygon(vertices).convex_hull.exterior.coords[:-1]
    return Polygon(convex_vertices)


def generate_map(width, height, num_obstacles, max_radius, max_vertices, max_attempts=1000):
    obstacles = []
    attempts = 0
    while len(obstacles) < num_obstacles and attempts < max_attempts:
        poly = generate_random_polygon(width, height, max_radius, max_vertices)
        if not any(poly.intersects(obs) for obs in obstacles):
            obstacles.append(poly)
        attempts += 1
    boundary = Polygon([(0, 0), (width, 0), (width, height), (0, height)])
    return boundary, obstacles


def build_graph_from_grid(cells, tol=1e-2):
    nodes = []
    cell_info = []
    from shapely.geometry import Polygon
    for cell in cells:
        # Versuche, Grenzen direkt zu verwenden, ansonsten aus Bounds
        if all(k in cell for k in ["x_left", "x_right", "y_top", "y_bottom"]):
            A_left = cell["x_left"]
            A_right = cell["x_right"]
            A_top = cell["y_top"]
            A_bottom = cell["y_bottom"]
        elif "bounds" in cell:
            A_left, A_top, A_right, A_bottom = cell["bounds"]
        else:
            poly = Polygon(cell["polygon"])
            A_left, A_top, A_right, A_bottom = poly.bounds
        cell_info.append({
            "number": cell["number"],
            "x_left": A_left,
            "x_right": A_right,
            "y_top": A_top,
            "y_bottom": A_bottom
        })
        poly = Polygon(cell["polygon"])
        centroid = poly.centroid
        nodes.append({
            "id": cell["number"],
            "centroid": (centroid.x, centroid.y)
        })
    links = []
    for i in range(len(cell_info)):
        for j in range(i + 1, len(cell_info)):
            A = cell_info[i]
            B = cell_info[j]
            # Horizontale Adjazenz
            if (abs(A["x_right"] - B["x_left"]) < tol or abs(B["x_right"] - A["x_left"]) < tol) and (
                    (A["y_top"] < B["y_bottom"] and A["y_bottom"] > B["y_top"]) or
                    (B["y_top"] < A["y_bottom"] and B["y_bottom"] > A["y_top"])):
                centroidA = ((A["x_left"] + A["x_right"]) / 2, (A["y_top"] + A["y_bottom"]) / 2)
                centroidB = ((B["x_left"] + B["x_right"]) / 2, (B["y_top"] + B["y_bottom"]) / 2)
                links.append({
                    "source": A["number"],
                    "target": B["number"],
                    "weight": math.hypot(centroidB[0] - centroidA[0], centroidB[1] - centroidA[1])
                })
            # Vertikale Adjazenz
            if (abs(A["y_bottom"] - B["y_top"]) < tol or abs(B["y_bottom"] - A["y_top"]) < tol) and (
                    (A["x_left"] < B["x_right"] and A["x_right"] > B["x_left"]) or
                    (B["x_left"] < A["x_right"] and B["x_right"] > A["x_left"])):
                centroidA = ((A["x_left"] + A["x_right"]) / 2, (A["y_top"] + A["y_bottom"]) / 2)
                centroidB = ((B["x_left"] + B["x_right"]) / 2, (B["y_top"] + B["y_bottom"]) / 2)
                links.append({
                    "source": A["number"],
                    "target": B["number"],
                    "weight": math.hypot(centroidB[0] - centroidA[0], centroidB[1] - centroidA[1])
                })
    return nodes, links


def find_nearest_node(point, G):
    best = None
    best_dist = float('inf')
    for n in G.nodes():
        node_data = G.nodes[n]  # Hier die Node-Daten holen
        d = math.hypot(node_data['centroid'][0] - point[0],
                       node_data['centroid'][1] - point[1])
        if d < best_dist:
            best_dist = d
            best = n
    return best
