// Draws every chord diagram widget on the page (metrics/widgets/chord.html).
// Each element points to a <script type="application/json"> with
// {nodes: [...], matrix: [[...]], main: [[...]]}, where matrix[i][j] is the
// number of courses Node i and Node j organised together and main[i][j] is the
// index of the pair's main Node (or null). Diagrams already drawn are skipped,
// so this file can be included once per widget.
(function () {
    const size = 520;
    const outer = size / 2 - 80;  // room for labels such as "EMBL-EBI"
    const inner = outer - 14;

    // "ELIXIR-SE" -> "SE"
    function shortName(node) {
        return node.replace(/^ELIXIR-/, "");
    }

    // Plotly's default colours, the same as the charts on the report pages.
    // With more than ten Nodes the colours repeat.
    const palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ];

    function nodeColours(count) {
        return d3.range(count).map(function (i) { return palette[i % palette.length]; });
    }

    document.querySelectorAll("[data-chord]").forEach(function (element) {
        if (element.dataset.drawn) {
            return;
        }
        element.dataset.drawn = "true";

        const data = JSON.parse(document.getElementById(element.dataset.chord).textContent);
        const chords = d3.chord().padAngle(0.04).sortSubgroups(d3.descending)(data.matrix);
        const colours = nodeColours(data.nodes.length);

        const svg = d3.select(element).append("svg")
            .attr("viewBox", [-size / 2, -size / 2, size, size])
            .attr("width", "100%")
            .style("height", "auto")
            .style("font", "13px sans-serif");

        // One ribbon per pair of Nodes, thicker for more shared courses,
        // coloured by the pair's main Node, or by the first Node if neither was main
        const ribbons = svg.append("g")
            .attr("fill-opacity", 0.7)
            .selectAll("path")
            .data(chords)
            .join("path")
            .attr("d", d3.ribbon().radius(inner))
            .attr("fill", function (d) {
                const main = data.main[d.source.index][d.target.index];
                return colours[main === null ? d.source.index : main];
            })
            .attr("stroke", "white")
            .attr("stroke-width", 0.5);

        ribbons.append("title")
            .text(function (d) {
                const count = d.source.value;
                return shortName(data.nodes[d.source.index]) + " – " + shortName(data.nodes[d.target.index])
                    + ": " + count + (count === 1 ? " course" : " courses");
            });

        // One band per Node, with its short name outside
        const group = svg.append("g")
            .selectAll("g")
            .data(chords.groups)
            .join("g")
            .style("cursor", "default");

        group.append("path")
            .attr("fill", function (d) { return colours[d.index]; })
            .attr("d", d3.arc().innerRadius(inner).outerRadius(outer))
            .append("title")
            .text(function (d) { return data.nodes[d.index]; });

        group.append("text")
            .each(function (d) { d.angle = (d.startAngle + d.endAngle) / 2; })
            .attr("dy", "0.35em")
            .attr("transform", function (d) {
                return "rotate(" + (d.angle * 180 / Math.PI - 90) + ")"
                    + " translate(" + (outer + 6) + ")"
                    + (d.angle > Math.PI ? " rotate(180)" : "");
            })
            .attr("text-anchor", function (d) { return d.angle > Math.PI ? "end" : null; })
            .attr("fill", "currentColor")
            .text(function (d) { return shortName(data.nodes[d.index]); });

        // Hovering a Node shows only its ribbons
        group
            .on("mouseenter", function (event, node) {
                ribbons.attr("fill-opacity", function (d) {
                    return d.source.index === node.index || d.target.index === node.index ? 0.85 : 0.08;
                });
            })
            .on("mouseleave", function () {
                ribbons.attr("fill-opacity", 0.7);
            });
    });
})();
