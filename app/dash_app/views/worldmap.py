from metrics.views.common import get_tabs
from django_plotly_dash import DjangoDash
from django.shortcuts import render
import plotly.express as px
from dash import dcc
from dash import html
import pandas as pd
import numpy as np
from django.db.models import Count, F, Sum, Q
from metrics.models import Event, Quality, Impact, Demographic, Node

def get_event_data():
    # Query database to get counts of events by country
    event_counts = Event.objects.filter(node_main=F('node')).values('location_country', 'node_main__name').annotate(count=Count('code', distinct=True))
    # Convert the QuerySet to a DataFrame
    df = pd.DataFrame(list(event_counts))
    total_events = df['count'].sum()
    temp = df.groupby('location_country').agg(lambda x: pd.Series.tolist(x))
    temp['aggregated']=temp[['node_main__name', 'count']].agg(lambda x: "; ".join(x[0][i] + ": " + str(x[1][i]) for i in range(len(x[0]))), axis=1)
    temp = temp.drop(columns=['node_main__name', 'count'])
    df = df.drop(columns=['node_main__name'])
    df = df.groupby('location_country').sum().reset_index()
    final = pd.merge(df, temp, on='location_country')
    return final, total_events


def get_general_statistics():
    events_with_metrics = Event.objects.filter(quality__isnull=False)
    metrics_count = {
        "demographic_count": Demographic.objects.count(),
        "impact_count": Impact.objects.count(),
        "quality_count": Quality.objects.count(),
        "events_count": Event.objects.all().count(),
        "events_with_metrics_count": events_with_metrics.distinct().count(),
        "events_with_metrics_participants": events_with_metrics.aggregate(sum=Sum("number_participants"))["sum"],
    }
    aggregates = Event.objects.all().aggregate(
        complete_duration=Sum("duration"),
        complete_participants=Sum("number_participants"),
        complete_trainers=Sum("number_trainers")
    )

    percentage = int(100 * metrics_count["quality_count"] / aggregates["complete_participants"])
    return {
        **metrics_count,
        **aggregates,
        "response_percentage": f"{percentage}%"
    }


def world_map(request):
    app = DjangoDash("WorldMap")

    try:
        df, total_events = get_event_data()
    except Exception as e:
        print(f"Error getting event data for map: {e}")
        return render(request, 'error.html', {"message": "Error getting event data for map."})
    
    df['log_count'] = np.log10(df['count'] + 0.1)
    
    fig = px.choropleth(df, locations='location_country', color='log_count',
                        locationmode='country names',
                        color_continuous_scale=["#ffffff", "#F47D20"],
                        title=f'Number of events per country (Total: {format(total_events, ",")})',
                        custom_data=['count', 'aggregated'],
                        height=600)

    fig.update_traces(hovertemplate='%{location} - %{customdata[0]} events<br>%{customdata[1]}<extra></extra>')

    max_log_count = np.ceil(df['log_count'].max())
    
    fig.update_layout(
        title={
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        geo=dict(
            showframe=False,
            showcoastlines=False,
            showcountries=True,
            countrywidth=0.2,
            lataxis_range=[-60, 90]
        ),
        coloraxis_colorbar=dict(
          title='Count',
          tickvals=[i for i in range(int(max_log_count)+1)],
          ticktext=[str(int(10**i)) for i in range(int(max_log_count)+1)],
        ),
    )

    app.layout = html.Div([
        dcc.Graph(id='choropleth', figure=fig)
    ])

    dash_config = {"dash_name": "WorldMap"}

    table_values = {
        "Total number of events": "events_count",
        "Total number of days of training": "complete_duration",
        "Total number of participants": "complete_participants",
        "Total number of trainers": "complete_trainers",
        "Total number of feedback responses (quality metrics) received": "quality_count",
        "Total number of events for which feedback (quality metrics) collected": "events_with_metrics_count",
        "Percentage of participants who provided feedback (quality metrics) for events where feedback was collected": "response_percentage"
    }
    stats = get_general_statistics()

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config,
            "title": "World map and statistics",
            "table": {
                "headings": ["Metric", "Value"],
                "items": [
                    [key, stats[item]]
                    for key, item in table_values.items()
                ]
            }
        }
    )
