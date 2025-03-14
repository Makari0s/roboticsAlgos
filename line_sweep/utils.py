import random, math
import networkx as nx
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union


# ----- Karten- und Hindernis-Generierung -----
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


# ----- Vertikale Linien -----
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


# ----- Graphaufbau aus Cells (für View 4) -----
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
            if (abs(A["x_right"] - B["x_left"]) < tol or abs(B["x_right"] - A["x_left"]) < tol) and not (
                    A["y_bottom"] <= B["y_top"] or B["y_bottom"] <= A["y_top"]):
                centroidA = ((A["x_left"] + A["x_right"]) / 2, (A["y_top"] + A["y_bottom"]) / 2)
                centroidB = ((B["x_left"] + B["x_right"]) / 2, (B["y_top"] + B["y_bottom"]) / 2)
                links.append({
                    "source": A["number"],
                    "target": B["number"],
                    "weight": math.hypot(centroidB[0] - centroidA[0], centroidB[1] - centroidA[1])
                })
            # Vertikale Adjazenz
            if (abs(A["y_bottom"] - B["y_top"]) < tol or abs(B["y_bottom"] - A["y_top"]) < tol) and not (
                    A["x_right"] <= B["x_left"] or B["x_right"] <= A["x_left"]):
                centroidA = ((A["x_left"] + A["x_right"]) / 2, (A["y_top"] + A["y_bottom"]) / 2)
                centroidB = ((B["x_left"] + B["x_right"]) / 2, (B["y_top"] + B["y_bottom"]) / 2)
                links.append({
                    "source": A["number"],
                    "target": B["number"],
                    "weight": math.hypot(centroidB[0] - centroidA[0], centroidB[1] - centroidA[1])
                })
    return nodes, links


# ----- Map Graph (View 2): Zusammenhängender Graph aus Arbeitsfläche, Hindernissen und vertical lines -----


def round_coord(p):
    return round(p[0], 5), round(p[1], 5)


def build_map_graph(width, height, obstacles, vertical_lines, tol=1e-5):
    G = nx.Graph()

    def print_graph_state(step):
        print(f"\n=== {step} ===")
        print("Knoten:", sorted(G.nodes()))
        print("Kanten:")
        for u, v, data in G.edges(data=True):
            print(f"  {u} <-> {v} | Gewicht: {data['weight']:.2f} | Typ: {data.get('type', '?')}")
        print()

    # 1. Workspace-Rahmen
    print("Initialisiere Workspace...")
    corners = [round_coord(p) for p in [(0, 0), (width, 0), (width, height), (0, height)]]
    G.add_nodes_from(corners)
    for i in range(4):
        u, v = corners[i], corners[(i + 1) % 4]
        length = LineString([u, v]).length
        G.add_edge(u, v, weight=length, type='workspace')
    print_graph_state("Initialer Workspace")

    # 2. Hindernisse hinzufügen
    print("\nVerarbeite Hindernisse...")
    for obs_idx, obs in enumerate(obstacles, 1):
        print(f"\nHindernis {obs_idx}:")
        coords = [round_coord(p) for p in obs.exterior.coords[:-1]]
        for i in range(len(coords)):
            u, v = coords[i], coords[(i + 1) % len(coords)]
            if u != v:
                length = LineString([u, v]).length
                print(f"  Füge Kante hinzu: {u} <-> {v} (Länge: {length:.2f})")
                G.add_edge(u, v, weight=length, type='obstacle', obstacle_id=obs_idx)
        print_graph_state(f"Nach Hindernis {obs_idx}")

    # 3. Vertikale Linien verarbeiten
    print("\nVerarbeite vertikale Linien...")
    vertical_lines = sorted(vertical_lines, key=lambda l: l['x'])

    for line_idx, line in enumerate(vertical_lines, 1):
        print(f"\n{'=' * 40}")
        print(f" Verarbeite Linie {line_idx} bei x={line['x']:.5f}")
        print(f"{'=' * 40}")

        x = round(line['x'], 5)
        source = round_coord(line['source'])
        y_up = round_coord((x, line['y_up']))
        y_down = round_coord((x, line['y_down']))

        print(f"  Source: {source}")
        print(f"  Y_Up:   {y_up}")
        print(f"  Y_Down: {y_down}")

        # Sammle alle Punkte und sortiere von oben nach unten
        all_points = [y_up, source, y_down]
        unique_points = []
        seen = set()
        for p in all_points:
            if p not in seen:
                seen.add(p)
                unique_points.append(p)

        # Sortiere nach Y-Koordinate (600=oben -> 0=unten)
        endpoints = sorted(unique_points, key=lambda p: -p[1])
        print(f"  Verarbeite Punkte (von oben nach unten): {endpoints}")

        # Prozessiere alle Punkte
        processed_nodes = []
        for p in endpoints:
            print(f"\n  ---- Verarbeite Punkt {p} ----")

            # Prüfe existierenden Knoten
            existing = next((n for n in G.nodes if n == p), None)
            if existing:
                print(f"  Knoten existiert bereits: {existing}")
                processed_nodes.append(existing)
                continue

            # Finde Kante zum Splitten
            edge_to_split = None
            for u, v in G.edges():
                if u == v:
                    continue

                edge_line = LineString([u, v])
                distance = edge_line.distance(Point(p))
                if distance < tol:
                    edge_to_split = (u, v)
                    print(f"  Gefundene Kante zum Splitten: {u} <-> {v}")
                    break

            # Führe Splitting durch
            if edge_to_split:
                u, v = edge_to_split
                print(f"  Splitte Kante {u} <-> {v} bei {p}")
                edge_data = G[u][v].copy()
                G.remove_edge(u, v)

                seg1_length = LineString([u, p]).length
                seg2_length = LineString([p, v]).length

                G.add_edge(u, p, **edge_data)
                G.add_edge(p, v, **edge_data)
                print(f"  Neue Kanten:")
                print(f"    {u} <-> {p} (Länge: {seg1_length:.2f})")
                print(f"    {p} <-> {v} (Länge: {seg2_length:.2f})")

            # Füge Knoten hinzu falls nötig
            if not G.has_node(p):
                G.add_node(p)
                print(f"  Neuer Knoten hinzugefügt: {p}")

            processed_nodes.append(p)

        # Verbinde alle Punkte vertikal
        print("\n  Verbinde vertikale Punkte:")
        for i in range(len(processed_nodes) - 1):
            upper = processed_nodes[i]
            lower = processed_nodes[i + 1]
            vertical_length = abs(upper[1] - lower[1])

            if not G.has_edge(upper, lower):
                print(f"  {upper} <-> {lower} (Länge: {vertical_length:.2f})")
                G.add_edge(upper, lower, weight=vertical_length, type='vertical')
            else:
                print(f"  Verbindung existiert bereits: {upper} <-> {lower}")

        print_graph_state(f"Zustand nach Linie {line_idx}")

    # Finale Bereinigung
    print("\nFühre finale Bereinigung durch...")
    G.remove_edges_from(nx.selfloop_edges(G))
    print_graph_state("Finaler Graph")

    return G


def print_graph_debug_info(G):
    """Gibt alle Knoten und ihre Nachbarn aus"""
    print("Knotenliste:")
    for node in sorted(G.nodes()):
        print(f"- {node}")

    print("\nKantenliste:")
    for u, v in sorted(G.edges()):
        print(f"{u} <-> {v}")

    print("\nNachbarn pro Knoten:")
    for node in sorted(G.nodes()):
        neighbors = sorted(G.neighbors(node))
        print(f"{node}:")
        for neighbor in neighbors:
            edge_data = G.get_edge_data(node, neighbor)
            print(f"  -> {neighbor} (Gewicht: {edge_data['weight']:.2f}, Typ: {edge_data.get('type', 'unbekannt')})")

    print("\nKnotengrade:")
    for node in sorted(G.nodes()):
        print(f"{node}: {G.degree[node]} Nachbarn")


def find_nearest_node(point, G):
    best = None
    best_dist = float('inf')
    for n in G.nodes():
        d = Point(n).distance(Point(point))
        if d < best_dist:
            best_dist = d
            best = n
    return best


def custom_traverse_face(G, start_edge, visited_edges):
    import math

    def calculate_angle(ref_vector, target_vector):
        """Berechnet den Winkel im Uhrzeigersinn von ref_vector zu target_vector (-180° bis 180°)"""
        # Berechnung von Dot- und Cross-Product
        dot = ref_vector[0] * target_vector[0] + ref_vector[1] * target_vector[1]
        cross = ref_vector[0] * target_vector[1] - ref_vector[1] * target_vector[0]

        # Winkel in Radiant und Umrechnung in Grad
        angle_rad = math.atan2(cross, dot)
        angle_deg = -math.degrees(angle_rad)  # Negation für Uhrzeigersinn

        # Normalisierung auf -180° bis 180°
        angle_deg = (angle_deg + 180) % 360 - 180

        return angle_deg

    # Initialisierung
    u, v = start_edge
    if u[1] < v[1]:  # Sicherstellen, dass die Kante von oben nach unten verläuft
        u, v = v, u

    print(f"\n=== Start Face Traversal from {u} -> {v} ===")
    face = [u, v]
    current_direction = (v[0] - u[0], v[1] - u[1])

    step = 0
    max_steps = len(G.nodes()) * 2  # Sicherheitsbegrenzung

    while step < max_steps:
        step += 1
        print(f"\n--- Step {step} ---")
        print(f"Current node: {v}")
        print(f"Current direction: {current_direction}")

        candidates = []
        previous_node = face[-2] if len(face) > 1 else None

        # Analysiere alle Nachbarn
        for w in G.neighbors(v):
            # Grundlegende Filter
            if w == previous_node:
                print(f"  Skip {w} (previous node)")
                continue
            if (v, w) in visited_edges or (w, v) in visited_edges:
                print(f"  Skip {w} (visited edge)")
                continue

            # Berechne Richtungsvektor
            direction_to_w = (w[0] - v[0], w[1] - v[1])

            # Berechne Winkel im Uhrzeigersinn
            angle = calculate_angle(current_direction, direction_to_w)

            print(f"  Candidate {w} | Angle: {angle:.2f}°")
            candidates.append((angle, w, direction_to_w))

        # Keine gültigen Kandidaten
        if not candidates:
            print("No valid candidates! Breaking...")
            break

        # Sortiere nach größtem Winkel (absteigend)
        candidates.sort(key=lambda x: -x[0])

        print("\nSorted candidates:")
        for i, (angle, w, _) in enumerate(candidates):
            print(f"{i + 1}. {w} ({angle:.2f}°)")

        # Wähle besten Kandidaten (größter Winkel)
        chosen_angle, chosen, new_direction = candidates[-1]
        print(f"\nChosen: {chosen} ({chosen_angle:.2f}°)")

        # Aktualisiere Zustand
        face.append(chosen)
        current_direction = new_direction

        # Endbedingung prüfen
        if chosen == face[0]:
            print("Face closed!")
            break

        v = chosen

    return face


def compute_custom_faces_from_graph(G, vertical_tol=1e-6):
    import networkx as nx
    from collections import defaultdict

    # Prüfe Planarität
    is_planar, embedding = nx.check_planarity(G)
    if not is_planar:
        raise ValueError("Graph is not planar!")

    # Bestimme den globalen rechten Rand (x-Koordinate)
    global_right = max(n[0] for n in G.nodes())
    print(f"Global right wall x-coordinate: {global_right}")

    # Sammle alle direkten vertikalen Kanten (ohne Umwege)
    vertical_edges = []
    for u, v in G.edges():
        if abs(u[0] - v[0]) < vertical_tol:  # Vertikale Kante
            # Sortiere die Kante konsistent (oben -> unten)
            if u[1] > v[1]:
                y_start, y_end = u[1], v[1]
                edge = (u, v)
            else:
                y_start, y_end = v[1], u[1]
                edge = (v, u)
            x = edge[0][0]

            # Überspringe Kanten, die zur rechten Wand gehören
            if abs(x - global_right) < vertical_tol:
                print(f"SKIP RIGHT WALL EDGE: {edge[0]} -> {edge[1]}")
                continue

            vertical_edges.append((edge[0], edge[1], x, y_start, y_end))

    # DEBUG: Ausgabe aller gesammelten vertikalen Kanten
    print("\n=== ALL VERTICAL EDGES (EXCLUDING RIGHT WALL) ===")
    for edge in vertical_edges:
        u, v, x, y1, y2 = edge
        print(f"Vertical edge: {u} -> {v} (x={x}, y_range=[{y2:.2f}, {y1:.2f}])")

    # Sortiere vertikale Kanten von RECHTS nach LINKS (x absteigend), bei gleichem x von OBEN nach UNTEN (y absteigend)
    vertical_edges.sort(key=lambda e: (-e[2], -e[3]))  # Wichtig: -e[2] für x, -e[3] für y
    print("\n=== SORTED VERTICAL EDGES ===")
    for edge in vertical_edges:
        u, v, x, y1, y2 = edge
        print(f"Sorted edge: {u} -> {v} (x={x}, y_top={y1:.2f})")

    faces = []
    visited_edges = set()
    processed_ranges = defaultdict(list)  # {x: [(y_start, y_end)]}

    for edge in vertical_edges:
        u, v, x, y_start, y_end = edge

        # DEBUG: Aktuellen verarbeiteten Bereich anzeigen
        print(f"\nProcessing edge: {u} -> {v}")
        print(f"Current processed ranges for x={x}: {processed_ranges[x]}")

        # Prüfe, ob diese Kante vollständig in einem existierenden Bereich liegt
        skip = False
        for (existing_start, existing_end) in processed_ranges[x]:
            if y_start <= existing_start and y_end >= existing_end:
                print(f"SKIP: Edge {u}->{v} is within processed range ({existing_start:.2f}, {existing_end:.2f})")
                skip = True
                break
        if skip:
            continue

        # Prüfe, ob die Kante bereits in einem Face enthalten ist
        edge_in_face = False
        for face in faces:
            for i in range(len(face) - 1):
                p, q = face[i], face[i + 1]
                if (p == u and q == v) or (p == v and q == u):
                    edge_in_face = True
                    break
            if edge_in_face:
                break
        if edge_in_face:
            print(f"SKIP: Edge {u}->{v} already in face")
            continue

        # Traversiere das Face
        print(f"\nSTARTING FACE TRAVERSAL for {u} -> {v}")
        face = custom_traverse_face(G, (u, v), visited_edges)
        if len(face) < 3:
            print("Invalid face (less than 3 nodes)")
            continue
        if face[0] != face[-1]:
            face.append(face[0])
        print(f"Found face: {face}")
        faces.append(face)

        # Füge den verarbeiteten Bereich hinzu
        processed_ranges[x].append((y_start, y_end))
        # Sortiere Bereiche für effiziente Prüfung
        processed_ranges[x].sort(reverse=True)
        print(f"Updated processed ranges for x={x}: {processed_ranges[x]}")

        # Markiere alle Kanten des Faces (außer vertikale der aktuellen Linie)
        for i in range(len(face) - 1):
            p, q = face[i], face[i + 1]
            if abs(p[0] - q[0]) < vertical_tol and abs(p[0] - x) < vertical_tol:
                continue
            visited_edges.add((p, q))
            visited_edges.add((q, p))

    return faces
