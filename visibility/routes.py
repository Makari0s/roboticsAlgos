from flask import render_template, jsonify, request
import random, math
import networkx as nx
from shapely.geometry import Polygon, LineString, Point
from . import visibility_bp
from .utils import generate_map, construct_visibility_graph, choose_valid_point

@visibility_bp.route('/')
def index():
    return render_template('visibility.html')

@visibility_bp.route('/graph_data_visibility')
def graph_data_visibility():
    width = int(request.args.get("width", 600))
    height = int(request.args.get("height", 600))
    num_obstacles = int(request.args.get("num_obstacles", 10))
    max_vertices = int(request.args.get("max_vertices", 6))
    obstacle_size = float(request.args.get("obstacle_size", 10))
    seed_str = request.args.get("seed", None)
    if seed_str is None:
        seed = random.randint(0, 1000000)
    else:
        seed = int(seed_str)
    random.seed(seed)

    boundary, obstacles = generate_map(width, height, num_obstacles, obstacle_size, max_vertices)
    # Hier verwenden wir alle Hindernisse – Erweiterungen (z. B. Obstacle Expansion) können später ergänzt werden
    used_obstacles = obstacles

    # Start und Ziel generieren (und validieren)
    start_x = float(request.args.get("start_x", 5))
    start_y = float(request.args.get("start_y", 5))
    goal_x = float(request.args.get("goal_x", width - 5))
    goal_y = float(request.args.get("goal_y", height - 5))
    start = (start_x, start_y)
    goal = (goal_x, goal_y)
    start = choose_valid_point(start, width, height, obstacles)
    goal = choose_valid_point(goal, width, height, obstacles)

    # Erzeuge den Visibility-Graphen – Kanten werden nur hinzugefügt, wenn an 25%, 50% und 75% der Strecke kein Hindernis liegt
    G = construct_visibility_graph(used_obstacles, start, goal)
    try:
        path = nx.shortest_path(G, source=start, target=goal, weight="weight")
    except nx.NetworkXNoPath:
        path = None

    # Knoten und Kanten für die Graph-Ansicht
    nodes = []
    node_index = {}
    for i, node in enumerate(G.nodes()):
        node_index[node] = i
        nodes.append({"id": i, "x": node[0], "y": node[1]})
    links = []
    for edge in G.edges(data=True):
        source = node_index[edge[0]]
        target = node_index[edge[1]]
        weight = edge[2]["weight"]
        links.append({"source": source, "target": target, "weight": weight})

    obs_data = [list(obs.exterior.coords)[:-1] for obs in obstacles]

    return jsonify({
        "nodes": nodes,
        "links": links,
        "path": path,
        "obstacles": obs_data,
        "start": {"x": start[0], "y": start[1]},
        "goal": {"x": goal[0], "y": goal[1]},
        "width": width,
        "height": height,
        "seed": seed
    })
