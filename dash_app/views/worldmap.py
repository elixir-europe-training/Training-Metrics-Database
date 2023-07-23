from .common import get_tabs
from django_plotly_dash import DjangoDash
from django.shortcuts import render
import plotly.express as px
from dash import dcc
from dash import html
import pandas as pd
from django.db.models import Count
from metrics.models import Event

def get_event_data():
    # Query database to get counts of events by country
    event_counts = Event.objects.values('location_country').annotate(count=Count('id'))

    # Convert the QuerySet to a DataFrame
    df = pd.DataFrame(list(event_counts))

    total_events = df['count'].sum()

    return df, total_events

def world_map(request):
    app = DjangoDash("WorldMap")

    try:
        df, total_events = get_event_data()
    except Exception as e:
        print(f"Error getting event data for map: {e}")
        return render(request, 'error.html', {"message": "Error getting event data for map."})

    fig = px.choropleth(df, locations='location_country', color='count',
                        locationmode='country names',
                        color_continuous_scale=px.colors.sequential.Viridis,
                        title=f'Number of events per country (Total: {format(total_events, ",")})')

    fig.update_traces(hovertemplate='%{location}<br>%{z}<extra></extra>')

    fig.update_layout(
        title={
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        })

    fig.update_geos(showcountries=True, countrywidth=0.2, countrycolor="Black",
                    lataxis_range=[-60, 90])

    app.layout = html.Div([
        dcc.Graph(id='choropleth', figure=fig, style={'width': '90vw', 'height': '70vh'})
    ])

    dash_config = {"dash_name": "WorldMap"}

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config
        }
    )
