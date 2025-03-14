console.log("quadtree.js loaded");

let currentData = null; // Cache der vollständigen Daten vom Full-Update
let lastValidStart = null;
let lastValidGoal = null;

// Update-Funktion: full==true: komplettes Update, full==false: nur Graph und Pfad aktualisieren.
function updateQuadTree(full = true) {
    const width = 600, height = 600;
    const params = {
        num_obstacles: document.getElementById("num_obstacles").value,
        max_vertices: document.getElementById("max_vertices").value,
        obstacle_size: document.getElementById("obstacle_size").value,
        max_depth: document.getElementById("max_depth").value,
        min_size: document.getElementById("min_size").value,
        start_x: document.getElementById("start_x").value,
        start_y: document.getElementById("start_y").value,
        goal_x: document.getElementById("goal_x").value,
        goal_y: document.getElementById("goal_y").value,
        seed: document.getElementById("seed").value || Date.now()
    };

    const url = `/quadtree/graph_data_quadtree?${new URLSearchParams(params)}`;
    console.log("Quadtree API URL:", url);
    d3.json(url).then(data => {
        console.log("Quadtree data:", data);
        currentData = data; // Speichern der kompletten Daten
        if (full) {
            drawMap(data);
            drawQuadtree(data);
        }
        drawGraph(data);
        drawPath(data);
        drawLegend(data);
        addDraggableMarkers(data);
        // Speichere die gültigen Start-/Zielkoordinaten
        lastValidStart = {x: data.start.x, y: data.start.y};
        lastValidGoal = {x: data.goal.x, y: data.goal.y};
    }).catch(error => {
        console.error("Error loading quadtree data:", error);
    });
}

// Hilfsfunktion: Ray Casting für Point in Polygon
function isPointInPolygon(point, polygon) {
    // polygon: Array von [x,y]-Punkten (geschlossener Ring, d.h. erster Punkt = letzter Punkt optional)
    let x = point.x, y = point.y;
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        let xi = polygon[i][0], yi = polygon[i][1];
        let xj = polygon[j][0], yj = polygon[j][1];
        let intersect = ((yi > y) !== (yj > y)) &&
                        (x < (xj - xi) * (y - yi) / (yj - yi + 0.0000001) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

function drawCoordinateGrid(svg, width, height, spacing = 50) {
    for (let x = 0; x <= width; x += spacing) {
        svg.append("line")
           .attr("x1", x)
           .attr("y1", 0)
           .attr("x2", x)
           .attr("y2", height)
           .attr("stroke", "#ddd")
           .attr("stroke-width", 1);
        svg.append("text")
           .attr("x", x + 2)
           .attr("y", 12)
           .text(x)
           .attr("font-size", "10px")
           .attr("fill", "#666");
    }
    for (let y = 0; y <= height; y += spacing) {
        svg.append("line")
           .attr("x1", 0)
           .attr("y1", y)
           .attr("x2", width)
           .attr("y2", y)
           .attr("stroke", "#ddd")
           .attr("stroke-width", 1);
        svg.append("text")
           .attr("x", 2)
           .attr("y", y - 2)
           .text(y)
           .attr("font-size", "10px")
           .attr("fill", "#666");
    }
}

function drawMap(data) {
    const svg = d3.select("#map_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    data.obstacles.forEach(obs => {
        svg.append("polygon")
           .attr("points", obs.map(p => p.join(",")).join(" "))
           .attr("fill", "darkgrey")
           .attr("stroke", "black");
    });
}

function drawQuadtree(data) {
    const svg = d3.select("#quadtree_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    data.cells.forEach(cell => {
        svg.append("polygon")
           .attr("points", cell.polygon.map(p => p.join(",")).join(" "))
           .attr("fill", cell.obstructed ? "#ffebee" : "#e8f5e9")
           .attr("stroke", cell.obstructed ? "#ffcdd2" : "#c8e6c9")
           .attr("stroke-width", 1);
    });
    data.obstacles.forEach(obs => {
        svg.append("polygon")
           .attr("points", obs.map(p => p.join(",")).join(" "))
           .attr("fill", "darkgrey")
           .attr("stroke", "black");
    });
}

function drawGraph(data) {
    const svg = d3.select("#graph_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    const nodeRadius = 12;
    data.graph.edges.forEach(edge => {
        svg.append("line")
           .attr("x1", edge.source[0])
           .attr("y1", edge.source[1])
           .attr("x2", edge.target[0])
           .attr("y2", edge.target[1])
           .attr("stroke", "#64B5F6")
           .attr("stroke-width", 3)
           .attr("opacity", 0.7);
    });
    svg.selectAll(".node")
        .data(data.graph.nodes)
        .enter()
        .append("circle")
        .attr("class", "node")
        .attr("cx", d => d.centroid[0])
        .attr("cy", d => d.centroid[1])
        .attr("r", nodeRadius)
        .attr("fill", "#1976D2")
        .attr("stroke", "white")
        .attr("stroke-width", 2);
    svg.selectAll(".node-label")
        .data(data.graph.nodes)
        .enter()
        .append("text")
        .attr("x", d => d.centroid[0])
        .attr("y", d => d.centroid[1])
        .text(d => d.id + 1)
        .attr("font-size", "14px")
        .attr("fill", "white")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central");
}

function drawPath(data) {
    const svg = d3.select("#graph_view");
    svg.selectAll("polyline.path").remove();
    if(data.path && data.path.length > 0) {
        // Erstelle Mapping: Knoten-ID zu Centroid
        let nodeMap = {};
        data.graph.nodes.forEach(n => {
            nodeMap[n.id] = n.centroid;
        });
        const pathPoints = data.path.map(id => nodeMap[id]);
        svg.append("polyline")
           .attr("class", "path")
           .attr("points", pathPoints.map(p => p.join(",")).join(" "))
           .attr("fill", "none")
           .attr("stroke", "purple")
           .attr("stroke-width", 3);
    }
}

function drawLegend(data) {
    const legendData = [
        {label: "Obstacles", color: "darkgrey"},
        {label: "Cells", color: "#e8f5e9"},
        {label: "Graph Nodes", color: "#1976D2"},
        {label: "Start", color: "green"},
        {label: "Goal", color: "blue"},
        {label: "Shortest Path", color: "purple"}
    ];
    d3.select("#legend").selectAll("*").remove();
    const legendSvg = d3.select("#legend").append("svg").attr("width", 300).attr("height", 150);
    legendSvg.selectAll("rect")
        .data(legendData)
        .enter()
        .append("rect")
        .attr("x", 10)
        .attr("y", (d, i) => 10 + i*25)
        .attr("width", 20)
        .attr("height", 20)
        .attr("fill", d => d.color);
    legendSvg.selectAll("text")
        .data(legendData)
        .enter()
        .append("text")
        .attr("x", 40)
        .attr("y", (d, i) => 25 + i*25)
        .text(d => d.label)
        .attr("font-size", "14px")
        .attr("fill", "#333");
}

//
// Draggable Marker-Funktion
//
function drawMarker(svg, point, label, color="orange", radius=8, markerClass="draggable-marker") {
    svg.append("circle")
       .attr("class", markerClass)
       .attr("cx", point.x)
       .attr("cy", point.y)
       .attr("r", radius)
       .attr("fill", color)
       .attr("stroke", "black")
       .attr("stroke-width", 2);
    svg.append("text")
       .attr("class", markerClass + "-label")
       .attr("x", point.x + radius + 2)
       .attr("y", point.y)
       .text(label)
       .attr("font-size", "14px")
       .attr("fill", "black")
       .attr("text-anchor", "middle")
       .attr("dominant-baseline", "middle");
}

function addDragBehavior(selection, type) {
    selection.call(d3.drag()
        .on("start", dragstarted)
        .on("drag", drag)
        .on("end", dragended));
}

function dragstarted(event, d) {
    const circle = d3.select(this);
    const [px, py] = d3.pointer(event, circle.node().ownerSVGElement);
    const currentX = +circle.attr("cx");
    const currentY = +circle.attr("cy");
    circle.attr("data-offset-x", currentX - px)
          .attr("data-offset-y", currentY - py);
}

function drag(event, d) {
    const circle = d3.select(this);
    const offsetX = +circle.attr("data-offset-x");
    const offsetY = +circle.attr("data-offset-y");
    const [px, py] = d3.pointer(event, circle.node().ownerSVGElement);
    const newX = px + offsetX;
    const newY = py + offsetY;
    circle.attr("cx", newX).attr("cy", newY);

    // Update Input-Felder
    if (circle.classed("start-marker")) {
        d3.select("#start_x").property("value", newX);
        d3.select("#start_y").property("value", newY);
    } else if (circle.classed("goal-marker")) {
        d3.select("#goal_x").property("value", newX);
        d3.select("#goal_y").property("value", newY);
    }
}

function dragended(event, d) {
    const circle = d3.select(this);
    circle.attr("data-offset-x", null).attr("data-offset-y", null);
    // Nach dem Drag: Überprüfe, ob der Marker in einem Hindernis liegt.
    let markerType = circle.classed("start-marker") ? "start" : "goal";
    let newX = +circle.attr("cx"), newY = +circle.attr("cy");
    let insideObstacle = false;
    // Prüfe für alle Hindernisse in currentData.obstacles (dieses Array enthält Polygonkoordinaten)
    currentData.obstacles.forEach(obs => {
        if (isPointInPolygon({x: newX, y: newY}, obs)) {
            insideObstacle = true;
        }
    });
    if (insideObstacle) {
        // Falls im Hindernis, setze Marker auf die letzte gültige Position zurück
        if (markerType === "start" && lastValidStart) {
            circle.attr("cx", lastValidStart.x).attr("cy", lastValidStart.y);
            d3.select("#start_x").property("value", lastValidStart.x);
            d3.select("#start_y").property("value", lastValidStart.y);
        } else if (markerType === "goal" && lastValidGoal) {
            circle.attr("cx", lastValidGoal.x).attr("cy", lastValidGoal.y);
            d3.select("#goal_x").property("value", lastValidGoal.x);
            d3.select("#goal_y").property("value", lastValidGoal.y);
        }
    }
    // Partial update: Nur Graph und Pfad aktualisieren
    updateQuadTree(false);
}

// Punkt-in-Polygon Funktion (Ray-Casting)
function isPointInPolygon(point, polygon) {
    let x = point.x, y = point.y;
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        let xi = polygon[i][0], yi = polygon[i][1];
        let xj = polygon[j][0], yj = polygon[j][1];
        let intersect = ((yi > y) !== (yj > y)) &&
                        (x < (xj - xi) * (y - yi) / ((yj - yi) || 0.0000001) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

// Partial update: nur Graph, Pfad und Marker aktualisieren (obstacles und quadtree bleiben unverändert)
function updateQuadTree(full = true) {
    const width = 600, height = 600;
    const params = {
        num_obstacles: document.getElementById("num_obstacles").value,
        max_vertices: document.getElementById("max_vertices").value,
        obstacle_size: document.getElementById("obstacle_size").value,
        max_depth: document.getElementById("max_depth").value,
        min_size: document.getElementById("min_size").value,
        start_x: document.getElementById("start_x").value,
        start_y: document.getElementById("start_y").value,
        goal_x: document.getElementById("goal_x").value,
        goal_y: document.getElementById("goal_y").value,
        seed: document.getElementById("seed").value || Date.now()
    };

    const url = `/quadtree/graph_data_quadtree?${new URLSearchParams(params)}`;
    console.log("Quadtree API URL:", url);
    d3.json(url).then(data => {
        console.log("Quadtree data:", data);
        // Bei full==true werden alle Views neu gezeichnet
        if (full) {
            drawMap(data);
            drawQuadtree(data);
        }
        // Unabhängig vom full-Flag: Graph und Pfad aktualisieren
        drawGraph(data);
        drawPath(data);
        drawLegend(data);
        addDraggableMarkers(data);
        // Aktualisiere letzte gültige Positionen
        lastValidStart = {x: data.start.x, y: data.start.y};
        lastValidGoal = {x: data.goal.x, y: data.goal.y};
        currentData = data;
    }).catch(error => {
        console.error("Error loading quadtree data:", error);
    });
}

function addDraggableMarkers(data) {
    const markerParams = [
        {view: "#map_view", type: "start", color: "green", label: "S"},
        {view: "#map_view", type: "goal", color: "blue", label: "Z"},
        {view: "#quadtree_view", type: "start", color: "green", label: "S"},
        {view: "#quadtree_view", type: "goal", color: "blue", label: "Z"},
        {view: "#graph_view", type: "start", color: "green", label: "S"},
        {view: "#graph_view", type: "goal", color: "blue", label: "Z"}
    ];

    markerParams.forEach(param => {
        const svg = d3.select(param.view);
        svg.selectAll(`.${param.type}-marker`).remove();
        svg.selectAll(`.${param.type}-marker-label`).remove();
        drawMarker(svg, data[param.type], param.type === "start" ? "S" : "Z", param.color, 8, param.type + "-marker");
        addDragBehavior(svg.select(`.${param.type}-marker`), param.type);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    updateQuadTree(true);
});
document.getElementById("reload").addEventListener("click", function() {
    updateQuadTree(true);
});
