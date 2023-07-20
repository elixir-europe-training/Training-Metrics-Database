import pandas as pd
import dash_bootstrap_components as dbc

from datetime import datetime
from functools import lru_cache

@lru_cache
def get_data(file_name):
    data = pd.read_csv(file_name)
    data['Start date'] = pd.to_datetime(data['Start date'], format='%d.%m.%Y')
    data['End date'] = pd.to_datetime(data['End date'], format='%d.%m.%Y')
    return data


class Group():
    def __init__(
        self,
        name,
        field_mapping,
        data,
        use_fields=None,
        filter_fields=[
            "event_type",
            "funding",
            "target_audience",
        ],
        graph_type="bar"
    ):
        self.data = data
        self.name = name
        self.fields = {
            field_mapping[name]: sorted([str(x) for x in set(data[name]) if str(x) != 'nan'])
            for name in use_fields
        } if use_fields else {
            field_id: sorted([str(x) for x in set(data[name]) if str(x) != 'nan'])
            for name, field_id in field_mapping.items()
        }
        self.field_mapping = field_mapping
        self.filter_fields = filter_fields
        self.graph_type = graph_type
    
    def get_graph_type(self):
        return self.graph_type

    def get_fields(self):
        return list(self.fields.keys())
    
    def get_filter_fields(self):
        return self.filter_fields
    
    def get_field_placeholder(self, field_id):
        return f"Select {self.get_field_title(field_id)}"
    
    def get_field_options(self, field_id):
        return self.fields[field_id]
    
    def get_field_title(self, lookup_id):
        for name, field_id in self.field_mapping.items():
            if lookup_id == field_id:
                return name
        return lookup_id
        
    
    def get_values(self, **params):
        data2 = self.data.copy()
        for field_id in self.filter_fields:
            value = params.get(field_id)
            if value is not None:
                data2 = data2[data2[self.get_field_title(field_id)] == value]

        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from is not None and date_to is not None:
            data2 = data2[(data2['Year'] >= date_from) & (data2['Year'] <= date_to)]
        if params.get("node_only"):
            data2 = data2[data2['Main organiser'] == 'ELIXIR-SE'] # CHANGE THIS to USER's node
        records = [
            {
                self.field_mapping[key]: value
                for key, value in row.items()
            }
            for row in data2.to_dict(orient='records')
        ]
        return records
    
    def get_name(self):
        return self.name


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups.get(name, None)


@lru_cache
def get_metrics():
    data = get_data('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')
    return Metrics(
        {
            "events": Group(
                "Events",
                {
                    '#': "id",
                    'Event code': "event_code",
                    'Title': "title",
                    'ELIXIR Node': "elixir_node",
                    'Start date': "start_date",
                    'End date': "end_date",
                    'Duration': "duration",
                    'Event type': "event_type",
                    'Funding': "funding",
                    'Organising Institution/s': "organizing_inititutions",
                    'Location (city, country)': "location",
                    'EXCELERATE subtask': "excelerate_subtask",
                    'Target audience': "target_audience",
                    'Additional ELIXIR Platforms involved': "additional_platforms",
                    'ELIXIR Communities involved': "communities_involved",
                    'Number of participants': "number_of_participants",
                    'Number of trainers/ facilitators': "number_of_trainers",
                    'Url to event page/ agenda': "url",
                    'Main organiser': "main_organizer",
                },
                data,
                use_fields=[
                    "Event type",
                    "Funding",
                    "Target audience",
                    "Location (city, country)"
                ]
            )
        }
    )

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", get_metrics())
        response = get_response(request)
        return response

    return middleware