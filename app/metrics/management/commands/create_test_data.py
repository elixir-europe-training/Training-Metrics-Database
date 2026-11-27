from django.core.management.base import BaseCommand
from uuid import uuid4
from metrics import models
from django.db.models import TextField
from typing import Callable
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
            default=0
        )
        parser.add_argument(
            "--contextid",
            type=str,
            required=False,
            default=uuid4()
        )
        parser.add_argument(
            "--event_ids",
            type=str,
            required=False,
            default="1,2,3"
        )
        parser.add_argument(
            "--valueformat",
            type=str,
            required=False,
            default="slug"
        )
        parser.add_argument(
            "--headerformat",
            type=str,
            required=False,
            default="slug"
        )
        parser.add_argument(
            "--responses",
            type=int,
            required=False,
            default=5
        )
        parser.add_argument(
            "--allanswers",
            action='store_true',
        )

    def handle(self, *args, **options):
        self.countries = list(models.common.country_mapping.keys())
        target_dir = options["targetdir"]
        events = options["events"]
        context_id = options["contextid"]

        responses = options["responses"]
        supersets = models.QuestionSuperSet.objects.filter(use_for_upload=True, is_active=True)
        (node, event_ids) = self.get_event_ids(options["event_ids"])
        use_slugs = options["valueformat"] == "slug"
        use_header_slugs = options["headerformat"] == "slug"
        use_all_answers = options["allanswers"]

        generators = [
            *(
                [(f"events-{context_id}.csv", self.create_event_data, (events,))]
                if events > 0
                else []
            ),
            *[
                (
                    f"metrics-{superset.slug}-{context_id}.csv",
                    self.create_data_from_questions,
                    (
                        [
                            question
                            for questionset in superset.question_sets.filter(is_active=True)
                            for question in questionset.questions.filter(is_active=True)
                        ],
                        event_ids,
                        responses,
                        use_slugs,
                        use_header_slugs,
                        use_all_answers,
                    )
                )
                for superset in supersets
            ]
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

    def get_event_ids(self, event_id_str: str):
        event_ids = []
        node = None
        if "system:" in event_id_str:
            (_, node_str, event_count_str) = event_id_str.split(":")
            event_count = int(event_count_str.strip())
            node = models.Node.objects.filter(name=node_str.strip()).get()
            event_ids = [
                event.id
                for event in models.Event.objects.filter(node_main=node, locked=False, code__isnull=True)[0:event_count]
            ]
        else:
            event_ids = [
                int(id_str.strip())
                for id_str in event_id_str.split(",")
            ]

        return (node, event_ids)

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

        return "|".join(random.choices(institutions, k=random.randint(1, 3)))

    def get_location(self):
        country = random.choice(self.countries or ["Sweden"])
        return f"Anywhere, {country}"

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
        test_data = get_test_data_from_model(
            models.Event,
            [
                (field_id, alias)
                for (alias, field_id) in event_mapping.items()
            ],
            count
        )
        test_data = update_table_rows(
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

    def create_data_from_questions(self, questions, event_ids, response_count, use_slugs, use_header_slugs, use_all_answers):
        headers = [question.slug if use_header_slugs else question.text for question in questions]
        data = [
            {
                "event_id": event_id,
                **{
                    (question.slug if use_header_slugs else question.text): self.create_data_from_question(question, use_slugs, use_all_answers)
                    for question in questions
                }
            }
            for event_id in event_ids
            for _ in range(0, response_count)
        ]
        return (
            [
                "event_id",
                *headers,
            ],
            data
        )

    def create_data_from_question(self, question, use_slugs, use_all_answers):
        answers = [
            answer.slug if use_slugs else answer.text
            for answer in question.answers.filter(is_active=True)
        ]
        answers = [
            a
            for a in answers
            if a != "-" or use_all_answers
        ]
        max_count = len(answers) if question.is_multichoice else 1
        count = random.randint(max_count if use_all_answers else 1, max_count)
        return "|".join(
            random.sample(answers, count)
        )


def get_test_data_from_model(model, fields: list[tuple[str, str]], number_of_samples: int) -> list[dict]:
    field_info = {
        field_id: {
            "alias": alias,
            **get_field_info(model, field_id)
        }
        for field_id, alias in fields
    }

    samples = [
        {
            info["alias"]: (
                (
                    ", ".join(
                        random.choices(info["values"], k=random.randint(1, len(info["values"])))
                    )
                    if info["multichoice"]
                    else random.choice(info["values"])
                )
                if info["values"] is not None
                else ""
            )
            for info in field_info.values()
        }
        for i in range(number_of_samples)
    ]
    return samples


def update_table_rows(
    table: list[dict],
    columns: dict[str, Callable[[], str] | None]
) -> list[dict]:
    new_data = []
    for row in table:
        new_row = row.copy()
        for (alias, generator) in columns.items():
            generator = (lambda: "") if generator is None else generator
            new_row[alias] = generator()
        new_data.append(new_row)
    return new_data


def get_field_info(model, field_id):
    field = model._meta.get_field(field_id)
    text_choices = (
        [
            c[0]
            for c in field.choices
        ]
        if type(field) is TextField and field.choices is not None
        else None
    )
    array_choices = (
        [
            c[0]
            for c in field.base_field.choices
        ]
        if type(field) is models.ChoiceArrayField
        else None
    )
    return {
        "id": field_id,
        "type": str(type(field)),
        "multichoice": type(field) is models.ChoiceArrayField,
        "values": array_choices or text_choices,
    }
