console.log("line_sweep_random.js loaded");

let currentData = null; // Speichert die zuletzt geladenen Daten
let lastValidStart = null;
let lastValidGoal = null;

// Update-Funktion: full == true: komplettes Neuzeichnen, false: Partial Update (nur Graph und Pfad)
function updateLineSweepRandom(full = true) {
    const width = 600, height = 600;
    const num_obstacles = document.getElementById("num_obstacles").value;
    const max_vertices = document.getElementById("max_vertices").value;
    const obstacle_size = document.getElementById("obstacle_size").value;
    const startX = document.getElementById("start_x").value;
    const startY = document.getElementById("start_y").value;
    const goalX = document.getElementById("goal_x").value;
    const goalY = document.getElementById("goal_y").value;

    const url = `/line_sweep/graph_data_line_sweep_random?width=${width}&height=${height}` +
                `&num_obstacles=${num_obstacles}&max_vertices=${max_vertices}&obstacle_size=${obstacle_size}` +
                `&start_x=${startX}&start_y=${startY}&goal_x=${goalX}&goal_y=${goalY}`;
    console.log("API URL:", url);
    d3.json(url).then(function(data) {
        console.log("Data received:", data);
        currentData = data;
        if (full) {
            drawObstacles(data);
            drawMapGraph(data);
            drawDecomposition(data);
        }
        drawCellsGraph(data);
        drawLegend();
        // Marker in allen Views
        addDraggableMarkers(data);
        // Speichere gültige Start-/Zielkoordinaten
        lastValidStart = {x: data.start.x, y: data.start.y};
        lastValidGoal = {x: data.goal.x, y: data.goal.y};
    }).catch(function(error) {
        console.error("Error:", error);
    });
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

function drawObstacles(data) {
    console.log("Obstacles:", data.obstacles);
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





function drawMapGraph(data) {
    const svg = d3.select("#map_graph_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    data.map_graph.edges.forEach(edge => {
        svg.append("line")
           .attr("x1", edge.source[0])
           .attr("y1", edge.source[1])
           .attr("x2", edge.target[0])
           .attr("y2", edge.target[1])
           .attr("stroke", "#666")
           .attr("stroke-width", 2);
    });
    data.map_graph.nodes.forEach(node => {
        svg.append("circle")
           .attr("cx", node.point[0])
           .attr("cy", node.point[1])
           .attr("r", 4)
           .attr("fill", "blue");
    });
}

function drawDecomposition(data) {
    const svg = d3.select("#decomposition_view");
    svg.selectAll("*").remove();
    data.faces.forEach((face, i) => {
        svg.append("polygon")
           .attr("points", face.map(p => p.join(",")).join(" "))
           .attr("fill", "lightgrey")
           .attr("stroke", "black")
           .attr("stroke-width", 1);
        let xs = face.map(p => p[0]);
        let ys = face.map(p => p[1]);
        let x_mid = xs.reduce((a, b) => a + b, 0) / xs.length;
        let y_mid = ys.reduce((a, b) => a + b, 0) / ys.length;
        svg.append("text")
           .attr("x", x_mid)
           .attr("y", y_mid)
           .text(i + 1)
           .attr("font-size", "16px")
           .attr("fill", "black")
           .attr("text-anchor", "middle")
           .attr("dominant-baseline", "central");
    });
    data.obstacles.forEach(obs => {
        svg.append("polygon")
           .attr("points", obs.map(p => p.join(",")).join(" "))
           .attr("fill", "none")
           .attr("stroke", "black")
           .attr("stroke-width", 2);
    });
}


function drawCellsGraph(data) {
    const svg = d3.select("#graph_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    const nodeRadius = 15;
    // Zeichne Kanten mit Randkorrektur
    data.face_graph.edges.forEach(edge => {
        const sourceNode = data.face_graph.nodes.find(n => n.id === edge.source);
        const targetNode = data.face_graph.nodes.find(n => n.id === edge.target);
        const dx = targetNode.centroid[0] - sourceNode.centroid[0];
        const dy = targetNode.centroid[1] - sourceNode.centroid[1];
        const length = Math.sqrt(dx*dx + dy*dy);
        if (length === 0) return;
        const ux = dx/length, uy = dy/length;
        const startX = sourceNode.centroid[0] + ux * nodeRadius;
        const startY = sourceNode.centroid[1] + uy * nodeRadius;
        const endX = targetNode.centroid[0] - ux * nodeRadius;
        const endY = targetNode.centroid[1] - uy * nodeRadius;
        svg.append("line")
           .attr("x1", startX)
           .attr("y1", startY)
           .attr("x2", endX)
           .attr("y2", endY)
           .attr("stroke", "#90CAF9")
           .attr("stroke-width", 3)
           .attr("opacity", 0.6);
    });
    // Zeichne Knoten (mit Schatten)
    const nodes = svg.selectAll(".face-node")
                     .data(data.face_graph.nodes)
                     .enter()
                     .append("g");
    nodes.append("circle")
         .attr("cx", d => d.centroid[0])
         .attr("cy", d => d.centroid[1])
         .attr("r", 15)
         .attr("fill", "#0D47A1")
         .attr("filter", "url(#drop-shadow)");
    nodes.append("circle")
         .attr("cx", d => d.centroid[0])
         .attr("cy", d => d.centroid[1])
         .attr("r", 15)
         .attr("fill", "#2196F3")
         .attr("stroke", "white")
         .attr("stroke-width", 2);
    nodes.append("text")
         .attr("x", d => d.centroid[0])
         .attr("y", d => d.centroid[1])
         .text(d => d.id + 1)
         .attr("font-size", "12px")
         .attr("fill", "white")
         .attr("font-weight", "bold")
         .attr("text-anchor", "middle")
         .attr("dominant-baseline", "central");
    // Pfad
    if (data.face_path && data.face_path.length > 0) {
        const pathPoints = data.face_path.map(id => {
            return data.face_graph.nodes.find(n => n.id === id).centroid;
        });
        let pathString = "";
        for (let i = 0; i < pathPoints.length - 1; i++) {
            const start = pathPoints[i], end = pathPoints[i + 1];
            const dx = end[0] - start[0], dy = end[1] - start[1];
            const len = Math.sqrt(dx*dx + dy*dy);
            if (len === 0) continue;
            const ux = dx/len, uy = dy/len;
            const startX = start[0] + ux * nodeRadius;
            const startY = start[1] + uy * nodeRadius;
            const endX = end[0] - ux * nodeRadius;
            const endY = end[1] - uy * nodeRadius;
            pathString += (i === 0 ? "M" : "L") + startX + "," + startY + " L" + endX + "," + endY + " ";
        }
        svg.append("path")
           .attr("d", pathString)
           .attr("fill", "none")
           .attr("stroke", "#B71C1C")
           .attr("stroke-width", 6)
           .attr("opacity", 0.3);
        svg.append("path")
           .attr("d", pathString)
           .attr("fill", "none")
           .attr("stroke", "#FF5252")
           .attr("stroke-width", 4)
           .attr("stroke-linecap", "round")
           .attr("stroke-linejoin", "round")
           .attr("marker-end", "url(#arrowhead)");
    }
    // Schattenfilter hinzufügen
    svg.append("filter")
       .attr("id", "drop-shadow")
       .append("feDropShadow")
       .attr("dx", 2)
       .attr("dy", 2)
       .attr("stdDeviation", 2)
       .attr("flood-color", "rgba(0,0,0,0.5)");
}

function drawLegend() {
    const legendData = [
        {label: "Obstacles", color: "darkgrey"},
        {label: "Map Graph", color: "#666"},
        {label: "Decomposition (Faces)", color: "lightgrey"},
        {label: "Cells Graph Nodes", color: "#2196F3"},
        {label: "Shortest Path", color: "#FF5252"}
    ];
    d3.select("#legend").selectAll("*").remove();
    const legendSvg = d3.select("#legend").append("svg").attr("width", 300).attr("height", 100);
    legendSvg.selectAll("rect")
        .data(legendData)
        .enter()
        .append("rect")
        .attr("x", 10)
        .attr("y", (d, i) => 10 + i*25)
        .attr("width", 20)
        .attr("height", 20)
        .attr("fill", d => d.color)
        .attr("stroke", "black")
        .attr("stroke-width", 1);
    legendSvg.selectAll("text")
        .data(legendData)
        .enter()
        .append("text")
        .attr("x", 40)
        .attr("y", (d, i) => 25 + i*25)
        .text(d => d.label)
        .attr("font-size", "16px")
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
    // Prüfe, ob der Marker in einem Hindernis liegt
    let markerType = circle.classed("start-marker") ? "start" : "goal";
    let newX = +circle.attr("cx"), newY = +circle.attr("cy");
    let insideObstacle = false;
    currentData.obstacles.forEach(obs => {
        if (isPointInPolygon({x: newX, y: newY}, obs)) {
            insideObstacle = true;
        }
    });
    if (insideObstacle) {
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
    updateLineSweepRandom(false);
}

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
    updateLineSweepRandom(true);
});
document.getElementById("reload").addEventListener("click", function() {
    updateLineSweepRandom(true);
});
