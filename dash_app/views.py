import dash
import plotly.graph_objs as go
import pandas as pd
import dash_bootstrap_components as dbc

from django.shortcuts import render
from django_plotly_dash import DjangoDash
from dash import dcc, html, dash_table
from dash.dependencies import Output, Input

from datetime import datetime

app = DjangoDash("SimpleExample")

# read data from csv for now. To be replaced with db queries
data = pd.read_csv('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')
data['Year'] = pd.to_numeric(data['Start date'].str.split('.').str[-1])

# Initialize the table with all event types and zero count
data['Number of events'] = 0
table_data_initial = data[['Event type', 'Number of events']].drop_duplicates().to_dict('records')

# extract values from all columns for plotting
event_type = sorted(list(set(data['Event type'])))
funding = [x for x in list(set(data['Funding'])) if str(x) != 'nan']
location = sorted(list(set(data['Location (city, country)'])))

# layout for the input parameters for filtering
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='event-type',
                options=[{'label': i, 'value': i} for i in event_type],
                value='Event_type'
            )
        ]),
        dbc.Col([
            dcc.Dropdown(
                id='funding-type',
                options=[{'label': i, 'value': i} for i in funding],
                value='funding'
            )
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dcc.DatePickerRange(
                id='date-picker-range',
                initial_visible_month=datetime.now(),
            ),
        ], width={'size': 2, 'offset': 0, 'order': '1'}),
        dbc.Col([
            dcc.Dropdown(
                id='location-picker',
                options=[{'label': i, 'value': i} for i in location],
                value='location'
            ),
        ], width={'size': 2, 'offset': 0, 'order': '2'})
    ]),
    dash_table.DataTable(
        id='event-table',
        columns=[{"name": 'Event type', "id": 'Event type'}, {"name": 'Events', "id": 'Events'}],
        data=table_data_initial,
        page_size=10,
        style_cell={'textAlign': 'left'},
    ),
    dbc.Row([
        dcc.Graph(
            id='event-type-graph',
            figure={
                'data': [
                    go.Histogram(
                        x=data['Event type'],
                        name='Events'
                    )
                ],
                'layout': go.Layout(
                    title='Event type',
                    xaxis={'title': 'Event type'},
                    yaxis={'title': 'No. of events'},
                )
            }
        )
    ])
])

# updating the plot and table
@app.callback(
    [Output('event-table', 'data'),
     Output('event-type-graph', 'figure')],
    [Input('location-picker', 'value'),
     Input('funding-type', 'value')]
)
def update_graph_and_table(location, funding):
    data2 = data.copy()  # copy the original data
    if location != 'location':
        data2 = data2[data2['Location (city, country)'] == location]

    if funding != 'funding':
        data2 = data2[data2['Funding'] == funding]

    figure = {
        'data': [
            go.Histogram(
                x=data2['Event type'],
                name='Events'
            )
        ],
        'layout': go.Layout(
            title='Event type',
            xaxis={'title': 'Event type'},
            yaxis={'title': 'No. of events'},
        )
    }

    # Group by 'Event type' and count the occurrences
    table_data = data2.groupby('Event type').size().reset_index(name='Events')
    table_data = table_data[['Event type', 'Events']].to_dict('records')

    return table_data, figure

def event_report(request):
    return render(
        request,
        'dash_app/template.html',
        context={
            **request.navigation,
            "tabs": [
                {"title": title, "url": url, "active": active}
                for title, url, active in [
                    ("Events", "", False),
                    ("Quality metrics", "", False),
                    ("Demographics metrics", "", False),
                    ("Impact metrics", "", True)
                ]
            ]
        }
    )
