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
        generators = [
            (f"events-{context_id}.csv", self.create_event_data, (events,)),
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
