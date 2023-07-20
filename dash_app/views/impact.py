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


app = DjangoDash("ImpactReport")


def get_callback(group):
    def update_graph_and_table(*filter_values):
        filters = list(zip([*group.get_filter_fields(), "date_from", "date_to", "node_only"], filter_values))
        metrics = group.get_values(**{
            "name": value
            for name, value in filters
        })
        
        def generate_table_and_figure(data, column, title):
            figure = {
                'data': [
                    go.Bar(
                        x=[],
                        y=[],
                    )
                ],
                'layout': go.Layout(
                    title=title,
                    xaxis={'title': 'No. of Events', 'tickfont': {'size': 10}},
                    yaxis={'title': column},
                )
            }
            return figure

        return [
            generate_table_and_figure(metrics, field_id, group.get_field_title(field_id))
            for field_id in group.get_fields()
        ]
    
    return update_graph_and_table


@lru_cache
def use_callback(app, group):
    app.callback(
        [
            Output(f'{field_id}-graph', 'figure')
            for field_id in group.get_fields()
        ],
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
                    dcc.Graph(id=f'{field_id}-graph')
                ])
                for field_id in group.get_fields()
            ]
        ])
    )


def impact_report(request):
    group = request.metrics.get_group('impact')
    app.layout = get_layout(app, group)
    use_callback(app, group)

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            "dash_name": "ImpactReport"
        }
    )


