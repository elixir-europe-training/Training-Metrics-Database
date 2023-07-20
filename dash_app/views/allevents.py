import pandas as pd
import dash_bootstrap_components as dbc

from django.shortcuts import render
from django_plotly_dash import DjangoDash
from dash import dcc, html, dash_table
from dash.dependencies import Output, Input

from datetime import datetime

app = DjangoDash("AllEvents")

# Read the data
data = pd.read_csv('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')

# convert dates to datetime
data['Start date'] = pd.to_datetime(data['Start date'], format='%d.%m.%Y')
data['End date'] = pd.to_datetime(data['End date'], format='%d.%m.%Y')

# extract values from all columns for filtering
event_type = sorted([str(x) for x in set(data['Event type']) if str(x) != 'nan'])
funding = sorted([str(x) for x in set(data['Funding']) if str(x) != 'nan'])

app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='event-code',
                options=[{'label': i, 'value': i} for i in sorted(list(set(data['Event code'])))],
                value=None,
                multi=False,
                placeholder="Select an Event Code",
            )
        ]),
        dbc.Col([
            dcc.Input(
                id='event-title',
                type='text',
                placeholder="Enter a Title",
            )
        ]),
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
    dbc.Row([
        dash_table.DataTable(
            id='event-table',
            columns=[{"name": i, "id": i} for i in ['Event code', 'Title', 'Start date', 'End date', 
                                                    'ELIXIR Node', 'Event details upload status', 
                                                    'Edit event details', 'Feedback', 'Demographics']],
            page_size=50,
            style_table={'overflowX': 'auto'},
            style_cell={
                'minWidth': '50px', 'maxWidth': '180px',
                'whiteSpace': 'normal',
                'textAlign': 'left'
            },
        )
    ])
])

@app.callback(
    Output('event-table', 'data'),
    [Input('event-code', 'value'),
     Input('event-title', 'value'),
     Input('event-type', 'value'),
     Input('funding-type', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('node-only-toggle', 'value')]
)
def update_table(event_code, event_title, event_type, funding, date_from, date_to, node_only):
    data2 = data.copy()

    # Define the required columns
    required_columns = ['Event code', 'Title', 'Start date', 'End date', 'ELIXIR Node', 
                        'Event details upload status', 'Edit event details', 'Feedback', 'Demographics']

    # Check if required columns are in the data, if not, add them with default or empty values
    for col in required_columns:
        if col not in data2.columns:
            data2[col] = ''

    if event_code is not None:
        data2 = data2[data2['Event code'] == event_code]
    if event_title is not None:
        data2 = data2[data2['Title'] == event_title]
    if event_type is not None:
        data2 = data2[data2['Event type'] == event_type]
    if funding is not None:
        data2 = data2[data2['Funding'] == funding]
    if date_from is not None and date_to is not None:
        date_from = datetime.strptime(date_from.split(' ')[0], '%Y-%m-%d')
        date_to = datetime.strptime(date_to.split(' ')[0], '%Y-%m-%d')
        data2 = data2[(data2['Start date'] >= date_from) & (data2['End date'] <= date_to)]
    if node_only:
        data2 = data2[data2['ELIXIR Node'] == 'ELIXIR-SE'] # Modify this to fit your use case

    table_data = data2[required_columns].to_dict('records')

    return table_data


def all_events(request):
    return render(
        request,
        'dash_app/template.html',
        context={
            "dash_name": "AllEvents"
        }
    )
