import dash
import plotly.graph_objs as go
import pandas as pd
import dash_bootstrap_components as dbc

from django.shortcuts import render
from django_plotly_dash import DjangoDash
from dash import dcc, html, dash_table
from dash.dependencies import Output, Input

from datetime import datetime
from .common import get_tabs

app = DjangoDash("SimpleExample")

# read data from csv
data = pd.read_csv('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')
data['Start date'] = pd.to_datetime(data['Start date'], format='%d.%m.%Y')
data['End date'] = pd.to_datetime(data['End date'], format='%d.%m.%Y')

# extract values from all columns for plotting
event_type = sorted(list(set(data['Event type'])))
funding = sorted([str(x) for x in set(data['Funding']) if str(x) != 'nan'])
target_audience = sorted([str(x) for x in set(data['Target audience']) if str(x) != 'nan'])
location = sorted(list(set(data['Location (city, country)'])))

# layout for the input parameters for filtering
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='event-type',
                options=[{'label': i, 'value': i} for i in event_type],
                value=None,
                multi=False,
                placeholder="Select an Event Type",
            )
        ]),
        dbc.Col([
            dcc.Dropdown(
                id='funding-type',
                options=[{'label': i, 'value': i} for i in funding],
                value=None,
                multi=False,
                placeholder="Select a Funding Type",
            )
        ]),
        dbc.Col([
            dcc.Dropdown(
                id='target-audience',
                options=[{'label': i, 'value': i} for i in target_audience],
                value=None,
                multi=False,
                placeholder="Select a Target Audience",
            )
        ]),
        dbc.Col([
            dcc.DatePickerRange(
                id='date-picker-range',
                initial_visible_month=datetime.now(),
            )
        ])
    ]),
    dbc.Row([
        dash_table.DataTable(
            id='event-table',
            columns=[{"name": i, "id": i} for i in ['Event type', 'Events']],
            page_size=10,
            style_cell={'textAlign': 'left'},
        ),
        dcc.Graph(id='event-type-graph')
    ]),
    dbc.Row([
        dash_table.DataTable(
            id='funding-table',
            columns=[{"name": i, "id": i} for i in ['Funding', 'Events']],
            page_size=10,
            style_cell={'textAlign': 'left'},
        ),
        dcc.Graph(id='funding-graph')
    ]),
    dbc.Row([
        dash_table.DataTable(
            id='audience-table',
            columns=[{"name": i, "id": i} for i in ['Target audience', 'Events']],
            page_size=10,
            style_cell={'textAlign': 'left'},
        ),
        dcc.Graph(id='audience-graph')
    ]),
])

# updating the plot and table
@app.callback(
    [Output('event-table', 'data'),
     Output('event-type-graph', 'figure'),
     Output('funding-table', 'data'),
     Output('funding-graph', 'figure'),
     Output('audience-table', 'data'),
     Output('audience-graph', 'figure')],
    [Input('event-type', 'value'),
     Input('funding-type', 'value'),
     Input('target-audience', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph_and_table(event_type_value, funding_value, target_audience_value, date_from, date_to):
    data2 = data.copy()
    if event_type_value is not None:
        data2 = data2[data2['Event type'] == event_type_value]
    if funding_value is not None:
        data2 = data2[data2['Funding'] == funding_value]
    if target_audience_value is not None:
        data2 = data2[data2['Target audience'] == target_audience_value]
    if date_from is not None and date_to is not None:
        data2 = data2[(data2['Year'] >= date_from) & (data2['Year'] <= date_to)]
    
    def generate_table_and_figure(data, column, title):
        table_data = data.groupby(column).size().reset_index(name='Events').to_dict('records')
        figure = {
            'data': [
                go.Bar(
                    x=[item[column] for item in table_data],
                    y=[item['Events'] for item in table_data],
                )
            ],
            'layout': go.Layout(
                title=title,
                xaxis={'title': 'No. of Events', 'tickfont': {'size': 10}},
                yaxis={'title': column},
            )
        }
        return table_data, figure
    
    event_table_data, event_figure = generate_table_and_figure(data2, 'Event type', 'Event Type')
    funding_table_data, funding_figure = generate_table_and_figure(data2, 'Funding', 'Funding')
    audience_table_data, audience_figure = generate_table_and_figure(data2, 'Target audience', 'Target Audience')

    return event_table_data, event_figure, funding_table_data, funding_figure, audience_table_data, audience_figure


def event_report(request):
    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            "dash_name": "SimpleExample"
        }
    )

