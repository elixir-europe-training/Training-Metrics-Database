import dash
import plotly.graph_objs as go
import dash_bootstrap_components as dbc

from dash import dcc, html, dash_table
from dash.dependencies import Output, Input

from datetime import datetime
from functools import lru_cache
from itertools import groupby

from django.urls import reverse

def get_tabs(request, view_name=None):
    metrics_groups = {
        group_id: group
        for group_id, group in request.metrics.groups.items()
        if group.is_tab
    }
    view_name = (
        request.resolver_match.view_name
        if view_name is None
        else view_name
    )
    user_input = (
        [
            ("Upload data", "upload-data", {}),
            ("Import from TeSS", "tess-import", {}),
            ("Browse events", "event-list", {}),
            ("All institutions", "institution-list", {})
        ]
        if request.user.is_authenticated
        else []
    )
    tabs = [
        {"title": title, "url": reverse(name, kwargs=kwargs)}
        for title, name, kwargs in [
            ("World map", "world-map", {}),
            *[
                (group.get_name(), "metrics-group-report", {"group_id": group_id})
                for group_id, group in metrics_groups.items()
            ],
            ("All events", "all-events", {}),
            *user_input,
        ]
    ]
    return {
        "tabs": [
            {**tab, "active": tab["url"] == request.path_info}
            for tab in tabs
        ]
    }

def calculate_metrics(data, column):
    column_values = [d.get(column) for d in data]
    count = {}
    for value in column_values:
        if value is not None:
            values = value if type(value) == list else [value]
            for v in values:
                count[v] = count.get(v, 0) + 1
    return count


def generate_bar(metrics, title, xaxis, yaxis):
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


def generate_pie(metrics, title, xaxis, yaxis):
    return {
        'data': [
            go.Pie(
                values=[value for value in metrics.values()],
                labels=[key for key in metrics.keys()],
            )
        ],
        'layout': go.Layout(
            title=title,
            xaxis={'title': xaxis, 'tickfont': {'size': 10}},
            yaxis={'title': yaxis},
            width=900,
            height=600,
            legend={
                "xanchor": "left",
                "yanchor": "top",
                "y": 0.5,
                "x": 1.05
            }
        )
    }


def get_callback(group):
    def update_graph_and_table(*filter_values):
        filters = list(zip([*group.get_filter_fields(), "date_from", "date_to", "node_only"], filter_values[:-len(group.get_fields())]))
        chart_types = filter_values[-len(group.get_fields()):]  # Last inputs are the chart types
        values = group.get_values(**{
            name: value
            for name, value in filters
        })
        outputs = []
        for field_id, chart_type in zip(group.get_fields(), chart_types):
            metrics = calculate_metrics(values, field_id)
            metrics = {
                group.get_field_option_name(field_id, option_id): count
                for option_id, count in metrics.items()
            }
            if chart_type == 'bar':
                outputs.append(generate_bar(
                    metrics,
                    group.get_field_title(field_id),
                    group.get_field_title(field_id),
                    group.get_name()
                ))
            else:
                outputs.append(generate_pie(
                    metrics,
                    group.get_field_title(field_id),
                    group.get_field_title(field_id),
                    group.get_name()
                ))
            # Append table data for DataTable component
            outputs.append([{"name": name, "value": value} for name, value in metrics.items()])
        
        return outputs
    
    return update_graph_and_table


def get_table_callback(group):
    def update_graph_and_table(*filter_values):
        filters = list(zip([*group.get_filter_fields(), "date_from", "date_to", "node_only"], filter_values))
        values = group.get_values(**{
            name: value
            for name, value in filters
        })

        table_values = [
            {
                key: ", ".join(value) if type(value) == list else value
                for key, value in row.items()
            }
            for row in values
        ]
        
        return [table_values]
    
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
            *[Input(field_id, 'value') for field_id in group.get_filter_fields()],
            Input('date-picker-range', 'start_date'),
            Input('date-picker-range', 'end_date'),
            Input('node-only-toggle', 'value'),
            *[Input(f"{field_id}-chart-type", "value") for field_id in group.get_fields()]
        ]
    )(get_callback(group))


@lru_cache
def use_table_callback(app, group):
    app.callback(
        [
            Output('data-table', 'data')
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
    )(get_table_callback(group))


def get_layout(app, group):
    fields = group.get_filter_fields()
    return (
        app.layout
    ) if app.layout else (
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Node Only: "),
                    dbc.Switch(id='node-only-toggle', value=False, style={"fontSize": 24})
                ], className='col-1'),
                dbc.Col([
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        initial_visible_month=datetime.now(),
                        display_format='YYYY-MM-DD',
                        style={'fontSize':14}
                    )
                ]),
            ]),
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
            ]),

            *[
                dbc.Row([
                    dash_table.DataTable(
                        id=f'{field_id}-table',
                        columns=[
                            {"name": group.get_field_title(field_id), "id": "name", "type": "text"},
                            {"name": group.get_name(), "id": "value", "type": "numeric"}
                        ],
                        page_size=10,
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'minWidth': '50px', 'maxWidth': '180px',
                            'whiteSpace': 'normal',
                            'textAlign': 'left',
                            'padding': '5px',
                            'fontFamily': 'Roboto, sans-serif'
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold',
                            'color': 'black',
                            'fontFamily': 'Roboto, sans-serif'
                        },
                        style_header_conditional=[
                            {
                                'if': {'column_id': 'value'},
                                'textAlign': 'right'
                            }
                        ],
                        style_data_conditional=[
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            },
                            {
                                'if': {'column_type': 'numeric'},
                                'textAlign': 'right'
                            }
                        ],
                        export_format='csv'
                    ),
                    dcc.Graph(id=f'{field_id}-graph'),
                    dcc.RadioItems(
                        id=f'{field_id}-chart-type',
                        options=[
                            {'label': 'Pie Chart', 'value': 'pie'},
                            {'label': 'Bar Chart', 'value': 'bar'}
                        ],
                        value='pie',
                        labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                    )
                ], className='pt-4 pb-4')
                for field_id in group.get_fields()
            ]
        ])
    )


def get_table_layout(app, group):
    filter_fields = group.get_filter_fields()
    fields = group.get_fields()
    return (
        app.layout
    ) if app.layout else (
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("Node Only: "),
                    dbc.Switch(id='node-only-toggle', value=False, style={"fontSize": 24}),
                ], className='col-1'),
                dbc.Col([
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        initial_visible_month=datetime.now(),
                        display_format='YYYY-MM-DD',
                        style={'fontSize':14}
                    )
                ]),
            ]),
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
                    for field_id in filter_fields
                ],
            ]),
            dbc.Row([
                dash_table.DataTable(
                    id='data-table',
                    columns=[{"name": i, "id": i} for i in fields],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'minWidth': '50px', 'maxWidth': '180px',
                        'whiteSpace': 'normal',
                        'textAlign': 'left',
                        'padding': '5px',
                        'fontFamily': 'Roboto, sans-serif'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'color': 'black',
                        'fontFamily': 'Roboto, sans-serif'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {'column_type': 'numeric'},
                            'textAlign': 'right'
                        }
                    ],
                    export_format='csv'
                )
            ], className='pt-4 pb-4')
        ])
    )