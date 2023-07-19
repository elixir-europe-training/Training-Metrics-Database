import dash
from dash import dcc
from dash import html
import plotly.graph_objs as go

# data
event_types = ["Hackathon", "Knowledge exchange workshop", "Training - blended", "Training - elearning", "Training - face to face"]
events = [27, 60, 12, 320, 1095]

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                go.Bar(
                    x=event_types,
                    y=events,
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

if __name__ == '__main__':
    app.run_server(debug=True)
