import random

import networkx as nx
from flask import render_template, jsonify, request
from shapely import Polygon, Point

from . import line_sweep_bp
from .utils import (
    generate_map,
    compute_vertical_lines, build_map_graph, find_nearest_node,
    compute_custom_faces_from_graph, print_graph_debug_info, build_graph_from_grid,
)


@line_sweep_bp.route('/')
def index():
    return render_template('line_sweep.html')


@line_sweep_bp.route('/graph_data_line_sweep_random')
def graph_data_line_sweep_random():
    # 1. Parameter parsing
    width = int(request.args.get("width", 600))
    height = int(request.args.get("height", 600))
    num_obstacles = int(request.args.get("num_obstacles", 3))
    max_vertices = int(request.args.get("max_vertices", 6))
    obstacle_size = float(request.args.get("obstacle_size", 100))
    seed = request.args.get("seed", str(random.randint(0, 1000000)))
    random.seed(int(seed))

    # 2. Map generieren
    boundary, obstacles = generate_map(width, height, num_obstacles, obstacle_size, max_vertices)
    obstacles_coords = [list(obs.exterior.coords)[:-1] for obs in obstacles]

    # 3. Map Graph erstellen
    v_lines = compute_vertical_lines(width, height, obstacles)
    G_map = build_map_graph(width, height, obstacles, v_lines)

    # 4. Faces berechnen
    faces = compute_custom_faces_from_graph(G_map, vertical_tol=1e-6)

    # 5. Face-Graph erstellen
    face_cells = [{
        "number": i,
        "polygon": face,
        "bounds": Polygon(face).bounds
    } for i, face in enumerate(faces)]

    face_nodes, face_links = build_graph_from_grid(face_cells)

    # 6. Pfadberechnung
    start = (float(request.args.get("start_x", 50)), float(request.args.get("start_y", 300)))
    goal = (float(request.args.get("goal_x", 550)), float(request.args.get("goal_y", 300)))

    # Finde Start/Ziel Faces
    start_face = next((i for i, face in enumerate(faces) if Polygon(face).contains(Point(start))), None)
    goal_face = next((i for i, face in enumerate(faces) if Polygon(face).contains(Point(goal))), None)

    # Berechne Face-Pfad
    face_path = []
    if start_face is not None and goal_face is not None:
        G_face = nx.Graph()
        G_face.add_nodes_from([(n["id"], {"centroid": n["centroid"]}) for n in face_nodes])
        G_face.add_edges_from([(l["source"], l["target"], {"weight": l["weight"]}) for l in face_links])

        try:
            face_path = nx.shortest_path(G_face, start_face, goal_face, weight="weight")
        except nx.NetworkXNoPath:
            pass

    # 7. Map-Pfad als Fallback
    map_path = None
    try:
        start_node = find_nearest_node(start, G_map)
        goal_node = find_nearest_node(goal, G_map)
        map_path = nx.shortest_path(G_map, start_node, goal_node, weight="weight")
    except nx.NetworkXNoPath:
        pass

    return jsonify({
        "obstacles": obstacles_coords,
        "map_graph": {
            "nodes": [{"point": n} for n in G_map.nodes()],
            "edges": [{"source": u, "target": v} for u, v in G_map.edges()]
        },
        "faces": [list(face) for face in faces],
        "face_graph": {
            "nodes": face_nodes,
            "edges": face_links
        },
        "face_path": face_path,
        "map_path": map_path,
        "start": {"x": start[0], "y": start[1]},
        "goal": {"x": goal[0], "y": goal[1]},
        "width": width,
        "height": height,
        "seed": seed
    })
