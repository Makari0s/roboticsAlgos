console.log("visibility.js loaded");

let currentSeed = 12345; // Beibehalten für Partial Updates
let currentData = null;   // Cache der aktuellen Daten

// Update-Funktion: full==true: vollständiges Neuzeichnen, full==false: nur Graph-Elemente aktualisieren
function updateGraph(full) {
    console.log("updateGraph called, full =", full);
    const width = 600, height = 600;
    const obstacleSize = document.getElementById("obstacle_size").value;
    const maxVertices = document.getElementById("max_vertices").value;
    const startX = document.getElementById("start_x").value;
    const startY = document.getElementById("start_y").value;
    const goalX = document.getElementById("goal_x").value;
    const goalY = document.getElementById("goal_y").value;

    // Beim Partial-Update den aktuellen Seed beibehalten, damit Hindernisse gleich bleiben
    const url = `/visibility/graph_data_visibility?width=${width}&height=${height}` +
                `&num_obstacles=3&max_vertices=${maxVertices}&obstacle_size=${obstacleSize}` +
                `&start_x=${startX}&start_y=${startY}&goal_x=${goalX}&goal_y=${goalY}` +
                `&seed=${currentSeed}`;
    console.log("API URL:", url);

    d3.json(url).then(function(data) {
        console.log("Data received:", data);
        currentData = data;
        if (full) {
            // Vollständiges Neuzeichnen: View 1 (Obstacles) neu zeichnen
            drawObstacles(data);
        }
        // In jedem Fall: Graph-Elemente neu zeichnen
        drawGraphElements(data);
        drawLegend();
        // (Marker werden im jeweiligen View in drawObstacles und drawGraph gesetzt)
    }).catch(function(error) {
        console.error("Error fetching data:", error);
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

// View 1: Zeichne nur Hindernisse und Marker
function drawObstacles(data) {
    const svg = d3.select("#obstacles_view");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    // Hier: Weniger Hindernisse und größere Darstellung – Fill als Grau
    data.obstacles.forEach((obs, i) => {
        svg.append("polygon")
           .attr("points", obs.map(p => p.join(",")).join(" "))
           .attr("fill", "grey")
           .attr("stroke", "black")
           .attr("stroke-width", 2);
    });
    // Zeichne Start-/Zielmarker in View 1
    drawMarker(svg, data.start, "S", "green", 8, "start-marker");
    drawMarker(svg, data.goal, "Z", "blue", 8, "goal-marker");
    addDragBehavior(d3.selectAll(".start-marker"), "start");
    addDragBehavior(d3.selectAll(".goal-marker"), "goal");
}

// View 2: Zeichne den Visibility-Graph (Kanten, Knoten, Pfad)
function drawGraphElements(data) {
    const svg = d3.select("#graph");
    svg.selectAll("*").remove();
    drawCoordinateGrid(svg, 600, 600);
    // Zeichne Kanten
    data.obstacles.forEach((obs, i) => {
        svg.append("polygon")
           .attr("points", obs.map(p => p.join(",")).join(" "))
           .attr("fill", "grey")
           .attr("stroke", "black")
           .attr("stroke-width", 2);
    });

    data.links.forEach(edge => {
        svg.append("line")
           .attr("x1", data.nodes[edge.source].x)
           .attr("y1", data.nodes[edge.source].y)
           .attr("x2", data.nodes[edge.target].x)
           .attr("y2", data.nodes[edge.target].y)
           .attr("stroke", "#999")
           .attr("stroke-opacity", 0.6)
           .attr("class", "graph-element");
    });
    // Zeichne Knoten (rote Punkte)
    svg.selectAll("circle.node")
       .data(data.nodes)
       .enter()
       .append("circle")
       .attr("class", "node graph-element")
       .attr("cx", d => d.x)
       .attr("cy", d => d.y)
       .attr("r", 4)
       .attr("fill", "red");
    // Zeichne Start und Ziel (draggable)
    const startCircle = svg.append("circle")
       .attr("class", "start graph-element draggable")
       .attr("cx", data.start.x)
       .attr("cy", data.start.y)
       .attr("r", 6)
       .attr("fill", "green");
    const goalCircle = svg.append("circle")
       .attr("class", "goal graph-element draggable")
       .attr("cx", data.goal.x)
       .attr("cy", data.goal.y)
       .attr("r", 6)
       .attr("fill", "blue");
    // Zeichne den kürzesten Pfad, falls vorhanden
    if (data.path) {
        svg.append("polyline")
           .attr("class", "graph-element")
           .attr("points", data.path.map(p => p.join(",")).join(" "))
           .attr("fill", "none")
           .attr("stroke", "purple")
           .attr("stroke-width", 3);
    }
    addDragBehavior(startCircle, "start");
    addDragBehavior(goalCircle, "goal");
}

function drawLegend() {
    const legendData = [
        {label: "Obstacles", color: "grey"},
        {label: "Graph Nodes", color: "red"},
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
    if (circle.classed("start") || circle.classed("start-marker")) {
        d3.select("#start_x").property("value", newX);
        d3.select("#start_y").property("value", newY);
    } else if (circle.classed("goal") || circle.classed("goal-marker")) {
        d3.select("#goal_x").property("value", newX);
        d3.select("#goal_y").property("value", newY);
    }
}

function dragended(event, d) {
    const circle = d3.select(this);
    circle.attr("data-offset-x", null).attr("data-offset-y", null);
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
    updateGraph(false);
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

document.addEventListener("DOMContentLoaded", function() {
    updateGraph(true);
});
document.getElementById("reload").addEventListener("click", function() {
    updateGraph(true);
});
