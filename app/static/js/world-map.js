// Draws every world map widget on the page (metrics/widgets/world-map.html).
// Each map element points to a <script type="application/json"> with its data.
// The page loads this file once, after the widgets.
(function () {
    document.querySelectorAll("[data-world-map]").forEach(function (element) {
        const data = JSON.parse(document.getElementById(element.dataset.worldMap).textContent);
        // Colours from static/css/widgets.css
        const style = getComputedStyle(element);
        const low = style.getPropertyValue("--tmd-accent-lightest").trim();
        const high = style.getPropertyValue("--tmd-accent").trim();

        const trace = {
            type: "choropleth",
            locationmode: "country names",
            locations: data.countries,
            z: data.counts,
            text: data.countries,
            colorscale: [[0, low], [1, high]],
            colorbar: {len: 0.6, thickness: 12, outlinewidth: 0},
            marker: {line: {color: "white", width: 0.5}},
            hovertemplate: "%{text}: %{z}<extra></extra>",
        };

        const layout = {
            geo: {
                bgcolor: "white",
                landcolor: "#E5ECF6",
                subunitcolor: "white",
                showland: true,
                showlakes: true,
                lakecolor: "white",
                projection: {type: "equirectangular", scale: 3.5},
                showframe: false,
                showcoastlines: false,
                showcountries: true,
                countrywidth: 0.2,
                center: {lon: 20, lat: 50},
            },
            margin: {t: 0, r: 0, b: 0, l: 0},
            height: 320,
        };

        Plotly.newPlot(element, [trace], layout, {
            showLink: false,
            responsive: true,
            topojsonURL: element.dataset.topojsonUrl,
        });
    });
})();
