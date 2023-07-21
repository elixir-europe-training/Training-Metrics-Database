import pandas as pd
import dash_bootstrap_components as dbc

from datetime import datetime
from functools import lru_cache
from contextlib import suppress

@lru_cache
def get_data(file_name):
    data = pd.read_csv(file_name)
    for date_id in ['Start date', 'End date']:
        if date_id in data:
            data[date_id] = pd.to_datetime(data[date_id], format='%d.%m.%Y')
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
        self.field_mapping = field_mapping
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.fields = {
            field_id: sorted([str(x) for x in set(data[self.get_field_title(field_id)]) if str(x) != 'nan'])
            for field_id in [*use_fields, *filter_fields]
        } if use_fields else {
            field_id: sorted([str(x) for x in set(data[name]) if str(x) != 'nan'])
            for name, field_id in self.field_mapping.items()
        }
        self.use_fields = use_fields if use_fields else list(self.fields.keys())
    
    def get_graph_type(self):
        return self.graph_type

    def get_fields(self):
        return self.use_fields
    
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
    groups = {}
    shared_data = None
    shared_mapping = {
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
    }
    with suppress(FileNotFoundError):
        event_data = get_data('https://raw.githubusercontent.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango/main/raw-tmd-data/all_events_expanded.csv')
        shared_data = event_data
        groups["events"] = Group(
            "Events",
            shared_mapping,
            event_data,
            use_fields=[
                "event_type",
                "funding",
                "target_audience",
                "location"
            ]
        )
    with suppress(FileNotFoundError):
        impact_data = get_data('./raw-tmd-data/all-node_impact_metrics.csv')
        impact_data = pd.merge(impact_data, shared_data, on="Event code")
        groups["impact"] = Group(
            "Impact",
            {
                **shared_mapping,
                'Event code': "event_code",
                'Title_x': "title",
                'Title_y': "event_title",
                'Which training event did you take part in?': "training_event",
                'How long ago did you attend the training?': "time_from_last_attendance",
                'What was your main reason for attending the training?': "attendance_reason",
                'What was your main reason for attending the training? (Other)': "attendance_reason_other",
                'How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?': "tool_frequency_before",
                'How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?': "tool_frequency_after",
                'Do you feel that you are able to explain to others what you learnt in the training?': "can_you_explain",
                'Do you feel that you are able to explain to others what you learnt in the training? (Other)': "can_you_explain_other",
                'Are you now able to use the tool(s)/ resource(s) covered in the training?': "tools_ability",
                'Are you now able to use the tool(s)/ resource(s) covered in the training? (Other)': "tools_ability_other",
                'How did the training event help with your work?': "how_did_event_help",
                'How did the training event help with your work? (Other)': "how_did_event_help_other",
                'Attending the training event led to/ facilitated': "facilitation",
                'Attending the training event led to/ facilitated: (Other)': "facilitation_other",
                'Please elaborate on any impact': "elaborated_impact",
                'How many people have you shared the skills and/or knowledge that you learned during the training, with?': "knowledge_transfer",
                'Would you recommend the training to others?': "recommend",
                'Any other comments?': "comments"
            },
            impact_data,
            use_fields=[
                "time_from_last_attendance",
                "attendance_reason",
                "tool_frequency_before",
                "tool_frequency_after",
                "can_you_explain",
                "tools_ability",
                "how_did_event_help",
                "facilitation",
                "knowledge_transfer",
                "recommend",
            ],
            graph_type="pie"
        )
    with suppress(FileNotFoundError):
        quality_data = get_data('./raw-tmd-data/all-node_quality_metrics.csv')
        quality_data = pd.merge(quality_data, shared_data, on="Event code")
        groups["quality"] = Group(
            "Quality",
            {
                **shared_mapping,
                'Event code': "event_code",
                'Title_x': "title",
                'Title_y': "event_title",
                'Have you used the tool(s)/resource(s) covered in the course before?': "used_tools_before",
                'Will you use the tool(s)/resource(s) covered in the course again?': "use_tools_again",
                'Would you recommend the course?': "recommend",
                'Please tell us your overall rating for the entire course': "overall_rating",
                'May we contact you by email in the future for more feeback?': "may_contact",
                'What part of the training did you enjoy the most?': "most_enjoyable",
                'What part of the training did you enjoy the least?': "least_enjoyable",
                'The balance of theoretical and practical content was': "theoretical_balance",
                'What other topics would you like to see covered in the future?': "other_topics",
                'Any other comments?': "comments"
            },
            quality_data,
            use_fields=[
                "recommend",
                "overall_rating",
                "may_contact",
            ],
            graph_type="pie"
        )
    with suppress(FileNotFoundError):
        quality_data = get_data('./raw-tmd-data/all-demographics.csv')
        quality_data = pd.merge(quality_data, shared_data, on="Event code")
        groups["demographic"] = Group(
            "Demographic",
            {
                **shared_mapping,
                'Event code': "event_code",
                'Title': "title",
                'Title_y': "event_title",
                'Where did you see the course advertised?': "heard_from",
                'What is your career stage?': "career_stage",
                'What is your employment sector?': "employment_sector",
                'What is your country of employment?': "employment_country",
                'What is your gender?': "gender",
            },
            quality_data,
            use_fields=[
                "heard_from",
                "career_stage",
                "gender",
            ],
            graph_type="pie"
        )
    return Metrics(groups)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", get_metrics())
        response = get_response(request)
        return response

    return middleware