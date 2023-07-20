import dash
import plotly.graph_objs as go
import dash_bootstrap_components as dbc

from django.shortcuts import render
from django_plotly_dash import DjangoDash
from dash import dcc, html, dash_table
from dash.dependencies import Output, Input

from datetime import datetime
from functools import lru_cache
from .common import get_tabs
from itertools import groupby


app = DjangoDash("ImpactReport")


def calculate_metrics(data, column):
    column_values = [d[column] for d in data]
    count = {}
    for v in column_values:
        count[v] = count.get(v, 0) + 1
    return count


def generate_figure(metrics, title, xaxis, yaxis):
    return {
        'data': [
            go.Bar(
                y=[value for value in metrics.values()],
                x=[key for key in metrics.keys()],
            )
        ],
        'layout': go.Layout(
            title=title,
            xaxis={'title': xaxis, 'tickfont': {'size': 10}},
            yaxis={'title': yaxis},
        )
    }


def generate_tables_and_figures(group, values):
    for field_id in group.get_fields():
        metrics = calculate_metrics(values, field_id)
        yield generate_figure(
            metrics,
            group.get_field_title(field_id),
            'No. of Events',
            group.get_field_title(field_id)
        )
        yield [
            {"name": name, "value": value}
            for name, value in metrics.items()
        ]


def get_callback(group):
    def update_graph_and_table(*filter_values):
        filters = list(zip([*group.get_filter_fields(), "date_from", "date_to", "node_only"], filter_values))
        values = group.get_values(**{
            name: value
            for name, value in filters
        })
        
        return list(generate_tables_and_figures(group, values))
    
    return update_graph_and_table


def get_outputs(group):
    for field_id in group.get_fields():
        yield Output(f'{field_id}-graph', 'figure')
        yield Output(f'{field_id}-table', 'data')


@lru_cache
def use_callback(app, group):
    app.callback(
        list(get_outputs(group)),
        [
            *[
                Input(field_id, 'value')
                for field_id in group.get_filter_fields()
            ],
            Input('date-picker-range', 'start_date'),
            Input('date-picker-range', 'end_date'),
            Input('node-only-toggle', 'value'),
        ]
    )(get_callback(group))


def get_layout(app, group):
    fields = group.get_filter_fields()
    return (
        app.layout
    ) if app.layout else (
        html.Div([
            dbc.Row([
                *[
                    dbc.Col([
                        dcc.Dropdown(
                            id=field_id,
                            options=[{'label': i, 'value': i} for i in group.get_field_options(field_id)],
                            value=None,
                            multi=False,
                            placeholder=group.get_field_placeholder(field_id),
                        )
                    ])
                    for field_id in fields
                ],
                dbc.Col([
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        initial_visible_month=datetime.now(),
                    )
                ]),
                dbc.Col([
                    html.Label("Node Only: "),
                    dbc.Switch(id='node-only-toggle', value=False)
                ]),
            ]),
            *[
                dbc.Row([
                    dash_table.DataTable(
                        id=f'{field_id}-table',
                        columns=[
                            {"name": group.get_field_title(field_id), "id": "name"},
                            {"name": 'Events', "id": "value"}
                        ],
                        page_size=10,
                        style_cell={'textAlign': 'left'},
                    ),
                    dcc.Graph(id=f'{field_id}-graph')
                ])
                for field_id in group.get_fields()
            ]
        ])
    )


def impact_report(request):
    group = request.metrics.get_group('events')
    dash_config = {}
    if group:
        app.layout = get_layout(app, group)
        use_callback(app, group)
        dash_config = {
            "dash_name": "ImpactReport"
        }

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config
        }
    )


