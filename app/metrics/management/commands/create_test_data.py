from django.core.management.base import BaseCommand
from uuid import uuid4
from metrics import import_utils, models
import csv
import random


class Command(BaseCommand):
    help = 'Create test data for upload'

    def add_arguments(self, parser):
        parser.add_argument(
            "--targetdir",
            type=str,
            required=False,
            default="test-data"
        )
        parser.add_argument(
            "--events",
            type=int,
            required=False,
            default=5
        )
        parser.add_argument(
            "--contextid",
            type=str,
            required=False,
            default=uuid4()
        )
        parser.add_argument(
            "--eventcodes",
            type=str,
            required=False,
            default="1,2,3"
        )

    def handle(self, *args, **options):
        target_dir = options["targetdir"]
        events = options["events"]
        context_id = options["contextid"]
        event_codes = options["eventcodes"].split(",")
        generators = [
            (f"events-{context_id}.csv", self.create_event_data, (events,)),
            (f"demographic_quality-{context_id}.csv", self.create_demographic_quality_metrics, (event_codes,)),
            (f"impact-{context_id}.csv", self.create_impact_metrics, (event_codes,)),
        ]

        for file_name, generator, params in generators:
            fieldnames, test_data = generator(*params)
            with open(f"{target_dir}/{file_name}", "w") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow({
                    fieldname: fieldname
                    for fieldname in fieldnames
                })
                for row in test_data:
                    writer.writerow(row)

    def get_institutions(self):
        institutions = [
            "https://ror.org/0576by029",
            "https://ror.org/05g3p2p60",
            "https://ror.org/0576by029",
            "https://ror.org/05g3p2p60",
            "https://ror.org/03xrhmk39",
            "https://ror.org/02hpadn98",
            "https://ror.org/01h1jbk91",
            "https://ror.org/03bndpq63",
            "https://ror.org/045f7pv37",
            "https://ror.org/03mstc592",
            "https://ror.org/02catss52",
            "https://ror.org/04wfr2810",
            "https://ror.org/03mstc592",
            "https://ror.org/045f7pv37",
            "https://ror.org/02nv7yv05",
            "https://ror.org/052rphn09",
            "https://ror.org/045f7pv37",
            "https://ror.org/03bndpq63",
            "https://ror.org/045f7pv37",
            "https://ror.org/03bndpq63",
            "https://ror.org/00enajs79",
            "https://ror.org/033m02g29",
            "https://ror.org/002n09z45",
            "https://ror.org/05f0yaq80",
            "https://ror.org/01fapfv42",
            "https://ror.org/02495e989",
            "https://ror.org/05kb8h459",
            "https://ror.org/048a87296",
            "https://ror.org/008x57b05",
            "https://ror.org/027m9bs27",
            "https://ror.org/03z77qz90",
            "https://ror.org/048a87296",
            "https://ror.org/03xrhmk39",
        ]

        return ",".join(random.choices(institutions, k=random.randint(1, 3)))

    def get_location(self):
        return "Neverland, Queenstown"

    def get_start_date(self):
        return "2024-06-10"

    def get_end_date(self):
        return "2024-06-12"

    def get_title(self):
        return f"A cool event {uuid4()}"

    def get_node(self):
        return "ELIXIR-UK"

    def get_url(self):
        return "https://neverland.local"

    def create_event_data(self, count):
        event_mapping = {
            "Event type": "type",
            "Funding": "funding",
            "Target audience": "target_audience",
            "Additional ELIXIR Platforms involved": "additional_platforms",
            "ELIXIR Communities involved": "communities",
            "No. of participants": "number_participants",
            "No. of trainers/ facilitators": "number_trainers",
            "Url to event page/ agenda": "url",
        }
        test_data = import_utils.get_test_data_from_model(
            models.Event,
            [
                (field_id, alias)
                for (alias, field_id) in event_mapping.items()
            ],
            count
        )
        test_data = import_utils.update_table_rows(
            test_data,
            {
                "Url to event page/ agenda": self.get_url,
                "ELIXIR Node": self.get_node,
                "Title": self.get_title,
                "EXCELERATE WP": None,
                "Location (city, country)": self.get_location,
                "Start Date": self.get_end_date,
                "End Date": self.get_start_date,
                "Organising Institution/s": self.get_institutions
            }
        )
        return (
            [
                "Title",
                "ELIXIR Node",
                "Start Date",
                "End Date",
                "Event type",
                "Funding",
                "Organising Institution/s",
                "Location (city, country)",
                "EXCELERATE WP",
                "Target audience",
                "Additional ELIXIR Platforms involved",
                "ELIXIR Communities involved",
                "No. of participants",
                "No. of trainers/ facilitators",
                "Url to event page/ agenda"
            ],
            test_data
        )

    def create_demographic_quality_metrics(self, event_codes):
        count = len(event_codes)
        demographic_mapping = {
            "Where did you see the course advertised?": "heard_from",
            "What is your career stage?": "career_stage",
            "What is your employment sector?": "employment_sector",
            "What is your country of employment?": "employment_country",
            "What is your gender?": "gender",
        }
        quality_mapping = {
            "Have you used the tool(s)/resource(s) covered in the course before?": "used_resources_before",
            "Will you use the tool(s)/resource(s) covered in the course again?": "used_resources_future",
            "Would you recommend the course?": "recommend_course",
            "Please tell us your overall rating for the entire course": "course_rating",
            "May we contact you by email in the future for more feedback?": "email_contact",
            "The balance of theoretical and practical content was": "balance",
        }

        demographic_data = import_utils.get_test_data_from_model(
            models.Demographic,
            [
                (field_id, alias)
                for (alias, field_id) in demographic_mapping.items()
            ],
            count
        )
        quality_data = import_utils.get_test_data_from_model(
            models.Quality,
            [
                (field_id, alias)
                for (alias, field_id) in quality_mapping.items()
            ],
            count
        )
        combined_data = [
            {
                **ddr,
                **qdr
            }
            for ddr, qdr in zip(demographic_data, quality_data)
        ]
        event_code_iterator = iter(event_codes)
        test_data = import_utils.update_table_rows(
            combined_data,
            {
                "event_code": lambda: next(event_code_iterator),
                "Any other comments?": None,
                "What other topics would you like to see covered in the future?": None,
                "What part of the training did you enjoy the least?": None,
                "What part of the training did you enjoy the most?": None,
            }
        )
        return (
            [
                "event_code",
                "Where did you see the course advertised?",
                "What is your career stage?",
                "What is your employment sector?",
                "What is your country of employment?",
                "What is your gender?",
                "Have you used the tool(s)/resource(s) covered in the course before?",
                "Will you use the tool(s)/resource(s) covered in the course again?",
                "Would you recommend the course?",
                "Please tell us your overall rating for the entire course",
                "May we contact you by email in the future for more feedback?",
                "What part of the training did you enjoy the most?",
                "What part of the training did you enjoy the least?",
                "The balance of theoretical and practical content was",
                "What other topics would you like to see covered in the future?",
                "Any other comments?",
            ],
            test_data
        )

    def create_impact_metrics(self, event_codes):
        count = len(event_codes)
        impact_mapping = {
            "Which training event did you take part in?": None,
            "How long ago did you attend the training?": "when_attend_training",
            "What was your main reason for attending the training?": "main_attend_reason",
            "What was your main reason for attending the training? (Other)": None,
            "How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?": "how_often_use_before",
            "How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?": "how_often_use_after",
            "Do you feel that you are able to explain to others what you learnt in the training?": "able_to_explain",
            "Do you feel that you are able to explain to others what you learnt in the training? (Other)": None,
            "Are you now able to use the tool(s)/ resource(s) covered in the training:": "able_use_now",
            "Are you now able to use the tool(s)/ resource(s) covered in the training: (Other)": None,
            "How did the training event help with your work? [select all that apply]": "help_work",
            "How did the training event help with your work? (Other)": None,
            "Attending the training event led to/ facilitated: [select all that apply]": "attending_led_to",
            "Attending the training event led to/ facilitated: (Other)": None,
            "Please elaborate on any impact": None,
            "How many people have you shared the skills and/or knowledge that you learned during the training, with?": "people_share_knowledge",
            "Would you recommend the training to others?": "recommend_others",
            "Any other comments?": None,
        }
        test_data = import_utils.get_test_data_from_model(
            models.Impact,
            [
                (field_id, alias)
                for (alias, field_id) in impact_mapping.items()
                if field_id is not None
            ],
            count
        )
        event_code_iterator = iter(event_codes)
        test_data = import_utils.update_table_rows(
            test_data,
            {
                **{
                    alias: None
                    for (alias, field_id) in impact_mapping.items()
                    if field_id is None
                },
                "event_code": lambda: next(event_code_iterator),
            }
        )
        return (
            [
                "event_code",
                "Which training event did you take part in?",
                "How long ago did you attend the training?",
                "What was your main reason for attending the training?",
                "What was your main reason for attending the training? (Other)",
                "How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?",
                "How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?",
                "Do you feel that you are able to explain to others what you learnt in the training?",
                "Do you feel that you are able to explain to others what you learnt in the training? (Other)",
                "Are you now able to use the tool(s)/ resource(s) covered in the training:",
                "Are you now able to use the tool(s)/ resource(s) covered in the training: (Other)",
                "How did the training event help with your work? [select all that apply]",
                "How did the training event help with your work? (Other)",
                "Attending the training event led to/ facilitated: [select all that apply]",
                "Attending the training event led to/ facilitated: (Other)",
                "Please elaborate on any impact",
                "How many people have you shared the skills and/or knowledge that you learned during the training, with?",
                "Would you recommend the training to others?",
                "Any other comments?",
            ],
            test_data
        )
