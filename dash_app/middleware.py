import pandas as pd
import dash_bootstrap_components as dbc

from datetime import datetime

data = pd.read_csv('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')

# convert dates to datetime
data['Start date'] = pd.to_datetime(data['Start date'], format='%d.%m.%Y')
data['End date'] = pd.to_datetime(data['End date'], format='%d.%m.%Y')

class Group():
    def __init__(self, fields):
        self.fields = fields
        self.field_mapping = {
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
            'ELIXIR Communities involved': "A",
            'Number of participants': "B",
            'Number of trainers/ facilitators': "C",
            'Url to event page/ agenda': "D",
            'Main organiser': "E",
        }

    def get_fields(self):
        return list(self.fields.keys())
    
    def get_filter_fields(self):
        return [
            "event_type",
            "funding",
            "target_audience",

        ]
    
    def get_field_placeholder(self, field_id):
        return field_id
    
    def get_field_options(self,field_id):
        return self.fields[field_id]
    
    def get_field_title(self,field_id):
        return field_id
    
    def get_values(self, event_type=None, funding=None, target_audience=None, date_from=None, date_to=None, node_only=False):
        data2 = data.copy()
        if event_type is not None:
            data2 = data2[data2['Event type'] == event_type]
        if funding is not None:
            data2 = data2[data2['Funding'] == funding]
        if target_audience is not None:
            data2 = data2[data2['Target audience'] == target_audience]
        if date_from is not None and date_to is not None:
            data2 = data2[(data2['Year'] >= date_from) & (data2['Year'] <= date_to)]
        if node_only:
            data2 = data2[data2['Main organiser'] == 'ELIXIR-SE'] # CHANGE THIS to USER's node
        records = [
            {
                self.field_mapping[key]: value
                for key, value in row.items()
            }
            for row in data2.to_dict(orient='records')
        ]
        return records


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups.get(name, None)


current_metric = Metrics(
    {
        "events": Group(
            {
                "event_type": sorted(list(set(data['Event type']))), 
                "funding": sorted([str(x) for x in set(data['Funding']) if str(x) != 'nan']), 
                "target_audience": sorted([str(x) for x in set(data['Target audience']) if str(x) != 'nan']),
                "location": sorted(list(set(data['Location (city, country)'])))
            }
        )
    }
)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", current_metric)
        response = get_response(request)
        return response

    return middleware