import random, math
import networkx as nx
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union


# === 1. Grundfunktionen zum Erzeugen der Karte ===

def generate_random_polygon(width, height, max_radius, max_vertices):
    """
    Generiert ein zufälliges konvexes Polygon (als Hindernis) innerhalb des Arbeitsbereichs.
    """
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
    """
    Generiert 'num_obstacles' zufällige Hindernisse innerhalb eines Rechtecks (width x height),
    sodass sich diese nicht überlappen. Gibt außerdem die Arbeitsflächenumrandung zurück.
    """
    obstacles = []
    attempts = 0
    while len(obstacles) < num_obstacles and attempts < max_attempts:
        poly = generate_random_polygon(width, height, max_radius, max_vertices)
        overlap = False
        for obs in obstacles:
            if poly.intersects(obs):
                overlap = True
                break
        if not overlap:
            obstacles.append(poly)
        attempts += 1
    boundary = Polygon([(0, 0), (width, 0), (width, height), (0, height)])
    return boundary, obstacles


# === 2. Vertikale Linien berechnen (Grundfunktion) ===

def _get_coords(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Point':
        return [(geometry.x, geometry.y)]
    elif geometry.geom_type in ['LineString', 'LinearRing']:
        return list(geometry.coords)
    elif geometry.geom_type.startswith('Multi'):
        return [pt for geom in geometry.geoms for pt in _get_coords(geom)]
    return []


def compute_vertical_lines(width, height, obstacles, epsilon=1e-5):
    """
    Für jeden Eckpunkt der Hindernisse werden vertikale Linien (nach OBEN und UNTEN) berechnet,
    bis entweder eine andere Hinderniskante oder die Wand (Rand) erreicht wird.
    """
    vertical_lines = []
    obstacle_union = unary_union(obstacles) if obstacles else Polygon()
    vertices = []
    for obs in obstacles:
        vertices.extend(list(obs.exterior.coords)[:-1])
    vertices = list(set(vertices))
    for x, y in vertices:
        x, y = round(x, 8), round(y, 8)
        # Linie nach OBEN
        p_test = Point(x, y + epsilon)
        if not obstacle_union.contains(p_test):
            ray = LineString([(x, y + epsilon), (x, height)])
            intersections = []
            for obs in obstacles:
                inter = obs.intersection(ray)
                if not inter.is_empty:
                    intersections.extend(_get_coords(inter))
            if intersections:
                closest = min(intersections, key=lambda p: p[1])
                vertical_lines.append({'x': x, 'y_up': closest[1], 'y_down': y, 'source': (x, y)})
            else:
                vertical_lines.append({'x': x, 'y_up': height, 'y_down': y, 'source': (x, y)})
        # Linie nach UNTEN
        p_test = Point(x, y - epsilon)
        if not obstacle_union.contains(p_test):
            ray = LineString([(x, y - epsilon), (x, 0)])
            intersections = []
            for obs in obstacles:
                inter = obs.intersection(ray)
                if not inter.is_empty:
                    intersections.extend(_get_coords(inter))
            if intersections:
                closest = max(intersections, key=lambda p: p[1])
                vertical_lines.append({'x': x, 'y_up': y, 'y_down': closest[1], 'source': (x, y)})
            else:
                vertical_lines.append({'x': x, 'y_up': y, 'y_down': 0, 'source': (x, y)})
    return vertical_lines


# === 3. Graph-Aufbau: Verbinde alle Elemente zu einem zusammenhängenden Graphen ===

def build_connected_graph(width, height, boundary, obstacles, vertical_lines, split_tol=1e-6):
    """
    Baut einen zusammenhängenden, planaren Graphen.

    - Fügt die Eckpunkte der Arbeitsfläche (boundary) und deren Kanten (Wände) hinzu.
    - Fügt für jedes Hindernis dessen Randpunkte (als Knoten) und Kanten als zyklischen Graphen hinzu.
    - Fügt alle vertikalen Linien hinzu (beide Endpunkte als Knoten, plus die Kante dazwischen).
    - Prüft für jeden vertikalen Linien-Endpunkt, ob er auf einer existierenden Kante liegt. Falls ja,
      wird diese Kante an dieser Stelle gespalten (d.h. der Endpunkt wird zwischen den beiden Knoten eingefügt).
    """
    G = nx.Graph()

    # Arbeitsbereich (Boundary)
    b_coords = list(boundary.exterior.coords)[:-1]
    for p in b_coords:
        G.add_node(p)
    for i in range(len(b_coords)):
        p1 = b_coords[i]
        p2 = b_coords[(i + 1) % len(b_coords)]
        G.add_edge(p1, p2, weight=LineString([p1, p2]).length)

    # Hindernisse: Für jedes Hindernis als zyklischen Graphen
    for obs in obstacles:
        coords = list(obs.exterior.coords)[:-1]
        for p in coords:
            G.add_node(p)
        for i in range(len(coords)):
            p1 = coords[i]
            p2 = coords[(i + 1) % len(coords)]
            G.add_edge(p1, p2, weight=LineString([p1, p2]).length)

    # Vertikale Linien hinzufügen:
    for line in vertical_lines:
        x = line['x']
        p_up = (x, line['y_up'])
        p_down = (x, line['y_down'])
        G.add_node(p_up)
        G.add_node(p_down)
        G.add_edge(p_up, p_down, weight=abs(line['y_up'] - line['y_down']))
        # Überprüfe, ob p_up auf einer existierenden Kante liegt
        for (u, v, d) in list(G.edges(data=True)):
            seg = LineString([u, v])
            if seg.distance(Point(p_up)) < split_tol and Point(p_up).distance(Point(u)) > split_tol and Point(
                    p_up).distance(Point(v)) > split_tol:
                G.remove_edge(u, v)
                G.add_edge(u, p_up, weight=LineString([u, p_up]).length)
                G.add_edge(p_up, v, weight=LineString([p_up, v]).length)
        # Analog für p_down
        for (u, v, d) in list(G.edges(data=True)):
            seg = LineString([u, v])
            if seg.distance(Point(p_down)) < split_tol and Point(p_down).distance(Point(u)) > split_tol and Point(
                    p_down).distance(Point(v)) > split_tol:
                G.remove_edge(u, v)
                G.add_edge(u, p_down, weight=LineString([u, p_down]).length)
                G.add_edge(p_down, v, weight=LineString([p_down, v]).length)

    return G


# === 4. Extrahiere alle Faces (kleinste Zyklen) aus dem Graphen ===

def compute_faces_from_graph(G):
    """
    Extrahiert einfache Zyklen (Faces) aus einem planaren Graphen.
    Hier verwenden wir einen einfachen Ansatz, der die cycle_basis()-Funktion von NetworkX nutzt.
    Hinweis: Dies liefert nicht immer alle Faces exakt, sollte aber als Ausgangspunkt dienen.
    """
    faces = nx.cycle_basis(G)
    # Filtere Kreise, die zu klein sind
    faces = [face for face in faces if len(face) >= 4]
    return faces


# === 5. Hilfsfunktion zum Finden des nächstgelegenen Knotens ===

def find_nearest_node(point, G):
    best = None
    best_dist = float('inf')
    for n in G.nodes():
        d = Point(n).distance(Point(point))
        if d < best_dist:
            best_dist = d
            best = n
    return best


# === 6. Komplette Pipeline als Beispiel ===

def main_pipeline(width, height, num_obstacles, max_radius, max_vertices):
    # Erzeuge Karte
    boundary, obstacles = generate_map(width, height, num_obstacles, max_radius, max_vertices)
    # Berechne vertikale Linien
    v_lines = compute_vertical_lines(width, height, obstacles)
    # Baue zusammenhängenden Graphen
    G = build_connected_graph(width, height, boundary, obstacles, v_lines)
    # Berechne Faces (freie Zellen)
    faces = compute_faces_from_graph(G)
    return boundary, obstacles, v_lines, G, faces


if __name__ == '__main__':
    width, height = 600, 600
    num_obstacles = 3
    max_radius = 100
    max_vertices = 6
    boundary, obstacles, v_lines, G, faces = main_pipeline(width, height, num_obstacles, max_radius, max_vertices)
    print("Graph Nodes:", G.number_of_nodes())
    print("Graph Edges:", G.number_of_edges())
    print("Anzahl Faces (Zellen):", len(faces))
    # Beispiel: Bestimme den kürzesten Pfad zwischen einem Start- und Zielpunkt (hier: linke obere Ecke und rechte untere Ecke)
    start = (0, 0)
    goal = (width, height)
    start_node = find_nearest_node(start, G)
    goal_node = find_nearest_node(goal, G)
    try:
        path = nx.shortest_path(G, source=start_node, target=goal_node, weight='weight')
        print("Kürzester Pfad:", path)
    except nx.NetworkXNoPath:
        print("Kein Pfad gefunden.")
