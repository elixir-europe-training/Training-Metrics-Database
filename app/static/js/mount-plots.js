function mountPlots(elements) {
    elements = Array.from(elements)
    for (element of elements) {
        mountPlot(element)
    }
}

function mountPlot(element) {
    const view = {
        elementId: element.id,
        data: JSON.parse(document.getElementById(element.getAttribute("data-value-id")).textContent),
        chartType: element.getAttribute("data-chart-type") || "pie",
    }

    const layouts = {
        pie: {
            xaxis: {
                title: "Options",
                tickfont: {size: 10}
            },
            yaxis: {title: "Number of answers"},
            width: 900,
            height: 600,
            legend: {
                xanchor: "left",
                yanchor: "top",
                y: 0.5,
                x: 1.05
            }
        },
        bar: {
            xaxis: {
                title: "Options",
                tickfont: {'size': 10}
            },
            yaxis: {title: "Number of answers"},
        }
    }

    const data = [
        view.chartType === "pie" ? {
            values: view.data.options.map(option => option.count),
            labels: view.data.options.map(option => option.label),
            type: "pie"
        } : {
            y: view.data.options.map(option => option.count),
            x: view.data.options.map(option => option.label),
            type: "bar"
        }
    ]
    const viewLayout = {
        title: {text: view.data.label},
        ...layouts[view.chartType]
    }
    Plotly.newPlot(view.elementId, data, viewLayout, {showLink: false, responsive: true});
}
