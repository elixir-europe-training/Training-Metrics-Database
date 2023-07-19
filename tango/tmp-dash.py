import dash
import plotly.graph_objs as go
import pandas as pd
import dash_bootstrap_components as dbc

from dash import dcc
from dash import html

from datetime import date, datetime

app = dash.Dash(__name__)

# read data from csv for now. To be replaced with db queries
data = pd.read_csv('../raw-tmd-data/all_events_expanded.csv')
data['Year'] = pd.to_numeric(data['Start date'].str.split('.').str[-1])

# extract values from all columns for plotting
event_type = sorted(list(set(data['Event type'])))
funding    = [x for x in list(set(data['Funding'])) if str(x) != 'nan']
location   = sorted(list(set(data['Location (city, country)'])))
#put rest of filtering variables here

# layout for the input parameters for filtering (NEEDS UPDATING)
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='event-type',
                options=[{'label': i, 'value': i} for i in event_type],
                value='Event_type'
        )]),
        dbc.Col([
            dcc.Dropdown(
                id='funding-type',
                options=[{'label': i, 'value': i} for i in funding],
                value='funding'
        )])
    ]),
    dbc.Row([
        dbc.Col([
            dcc.DatePickerRange(
            id='date-picker-range',
            initial_visible_month=datetime.now(),
            ),
        ], width={'size':2,'offset':0,'order':'1'}),
        dbc.Col([
            dcc.Dropdown(
                id='location-picker',
                options=[{'label': i, 'value': i} for i in location],
                value='location'
            ),
        ], width={'size':2,'offset':0,'order':'2'})
    ]),
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
                title='Event Type Bar Plot',
                xaxis={'title': 'Event Types'},
                yaxis={'title': 'Number of Events'},
            )
        }
    )
    ])
    
])


# updating the plot
@app.callback(
    dash.dependencies.Output('event-type-graph', 'figure'),
    [dash.dependencies.Input('location-picker', 'value'),
     dash.dependencies.Input('funding-type', 'value')])
def update_graph(location, funding):
    data2 = data['Event type']
    if location != 'location':
        data2 = data[data['Location (city, country)'] == location]['Event type']
    
    if funding != 'funding':
        data2 = data[data['Funding'] == funding]['Event type']
    
  #  data2 = data[(data['Location (city, country)'] == location) & (data['Funding'] == funding)]

    return {
        'data': [
                go.Histogram(
                    x=data2,
                    name='Events'
                )
            ],
            'layout': go.Layout(
                title='Event Type Bar Plot',
                xaxis={'title': 'Event Types'},
                yaxis={'title': 'Number of Events'},
            )
    }



if __name__ == '__main__':
    app.run_server(debug=True)
