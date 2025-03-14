from flask import Blueprint, render_template, jsonify, request
import random
from shapely.geometry import Polygon, Point
from . import quad_tree_bp
from .utils import generate_map, QuadtreeCell, build_graph_from_grid, find_nearest_node
import networkx as nx

@quad_tree_bp.route('/')
def index():
    return render_template('quadtree.html')

@quad_tree_bp.route('/graph_data_quadtree')
def graph_data_quadtree():
    width = int(request.args.get("width", 600))
    height = int(request.args.get("height", 600))
    num_obstacles = int(request.args.get("num_obstacles", 3))
    max_vertices = int(request.args.get("max_vertices", 6))
    obstacle_size = float(request.args.get("obstacle_size", 100))
    max_depth = int(request.args.get("max_depth", 5))
    min_size = float(request.args.get("min_size", 20))
    seed = request.args.get("seed", str(random.randint(0, 1000000)))
    random.seed(int(seed))

    boundary, obstacles = generate_map(width, height, num_obstacles, obstacle_size, max_vertices)
    obstacles_coords = [list(obs.exterior.coords)[:-1] for obs in obstacles]

    root = QuadtreeCell((0, 0, width, height), max_depth=max_depth, min_size=min_size)
    root.check_obstruction(obstacles)
    root.subdivide(obstacles)

    quadtree_cells = []
    def collect_cells(cell):
        if not cell.children:
            quadtree_cells.append({
                "number": len(quadtree_cells),
                "polygon": [
                    [cell.bounds[0], cell.bounds[1]],
                    [cell.bounds[2], cell.bounds[1]],
                    [cell.bounds[2], cell.bounds[3]],
                    [cell.bounds[0], cell.bounds[3]]
                ],
                "bounds": cell.bounds,
                "obstructed": cell.is_obstructed
            })
        else:
            for child in cell.children:
                collect_cells(child)
    collect_cells(root)

    nodes, links = build_graph_from_grid([c for c in quadtree_cells if not c['obstructed']])
    G = nx.Graph()
    G.add_nodes_from([(n['id'], n) for n in nodes])
    G.add_edges_from([(l['source'], l['target'], {'weight': l['weight']}) for l in links])
    path = []
    try:
        start = (float(request.args.get("start_x", 50)), float(request.args.get("start_y", 300)))
        goal = (float(request.args.get("goal_x", 550)), float(request.args.get("goal_y", 300)))
        start_node = find_nearest_node(start, G)
        goal_node = find_nearest_node(goal, G)
        path = nx.shortest_path(G, start_node, goal_node, weight='weight')
    except nx.NetworkXNoPath:
        pass

    return jsonify({
        "obstacles": obstacles_coords,
        "cells": quadtree_cells,
        "graph": {
            "nodes": nodes,
            "edges": links
        },
        "path": path,
        "start": {"x": float(request.args.get("start_x", 50)), "y": float(request.args.get("start_y", 300))},
        "goal": {"x": float(request.args.get("goal_x", 550)), "y": float(request.args.get("goal_y", 300))},
        "params": {
            "max_depth": max_depth,
            "min_size": min_size,
            "seed": seed
        }
    })
