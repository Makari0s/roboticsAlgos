import random, math

import networkx as nx
from shapely.geometry import Polygon, Point, LineString


def generate_random_polygon(width, height, max_radius, max_vertices):
    cx = random.uniform(max_radius, width - max_radius)
    cy = random.uniform(max_radius, height - max_radius)
    n = random.randint(3, max_vertices)
    angles = sorted([random.uniform(0, 2 * math.pi) for _ in range(n)])
    vertices = []
    for angle in angles:
        r = random.uniform(max_radius / 2, max_radius)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        vertices.append((x, y))
    # Zur Garantie der Konvexität: Erzeuge die konvexe Hülle der Punkte.
    return Polygon(vertices).convex_hull


def generate_map(width, height, num_obstacles, max_radius, max_vertices):
    obstacles = []
    for _ in range(num_obstacles):
        poly = generate_random_polygon(width, height, max_radius, max_vertices)
        obstacles.append(poly)
    boundary = Polygon([(0, 0), (width, 0), (width, height), (0, height)])
    return boundary, obstacles


def construct_visibility_graph(obstacles, start, goal, sample_count=10):
    """
    Erzeugt einen Visibility-Graphen aus den Hindernissen und den Punkten start und goal.
    Eine Kante wird nur aufgenommen, wenn sie nicht durch irgendein Hindernis geht.
    Zunächst wird mit line.crosses(obs) geprüft – zusätzlich werden sample_count-1 Punkte
    entlang der Kante getestet, ob sie innerhalb eines Hindernisses liegen.
    """
    # Sammle alle Eckpunkte aus allen Hindernissen
    vertices = []
    for obs in obstacles:
        # Verwende alle Eckpunkte (ohne Wiederholung des letzten Punkts)
        vertices.extend(list(obs.exterior.coords)[:-1])
    vertices.append(start)
    vertices.append(goal)
    # Entferne Duplikate
    vertices = list(set(vertices))

    G = nx.Graph()
    n = len(vertices)
    for i in range(n):
        for j in range(i + 1, n):
            p1 = vertices[i]
            p2 = vertices[j]
            line = LineString([p1, p2])
            valid = True

            # Erstprüfung: Falls die Linie ein Hindernis schneidet, verwerfen.
            for obs in obstacles:
                if line.crosses(obs):
                    valid = False
                    break
            if not valid:
                continue

            # Zweitprüfung: Abtastung entlang der Linie
            for k in range(1, sample_count):
                t = k / sample_count
                pt = line.interpolate(t, normalized=True)
                for obs in obstacles:
                    if pt.within(obs):
                        valid = False
                        break
                if not valid:
                    break

            if valid:
                G.add_edge(p1, p2, weight=line.length)
    return G


def choose_valid_point(default, width, height, obstacles, margin=5, attempts=100):
    """
    Prüft, ob der Standardpunkt außerhalb aller Hindernisse liegt.
    Falls nicht, wird nach einer zufälligen, gültigen Position gesucht.
    """
    p = Point(default)
    if not any(obs.contains(p) for obs in obstacles):
        return default
    for _ in range(attempts):
        candidate = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
        if not any(obs.contains(Point(candidate)) for obs in obstacles):
            return candidate
    return default
