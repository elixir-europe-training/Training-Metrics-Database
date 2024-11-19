import csv
from metrics.models import (
    Event,
    Demographic,
    Quality,
    Impact,
    Node,
    OrganisingInstitution,
    User,
    Question,
    QuestionSet,
    QuestionSuperSet,
    Answer
)
from metrics import import_utils
from django.core.management.base import BaseCommand
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.template.defaultfilters import slugify


def get_data_sources(targetdir="example-data"):
    return {
        Event:  f'raw-tmd-data/{targetdir}/tango_events.csv',
        Demographic: f'raw-tmd-data/{targetdir}/tango_demographics.csv',
        Quality: f'raw-tmd-data/{targetdir}/tango_qualities.csv',
        Impact: f'raw-tmd-data/{targetdir}/tango_impacts.csv',
        User: f'raw-tmd-data/{targetdir}/users.csv',
        OrganisingInstitution: f'raw-tmd-data/{targetdir}/institutions.csv',
        Node: f'raw-tmd-data/{targetdir}/nodes.csv',
        Question: f'raw-tmd-data/{targetdir}/base_questions.csv',
        Answer: f'raw-tmd-data/{targetdir}/base_answers.csv',
    }


DATA_SOURCES = get_data_sources()
import_context = import_utils.ImportContext()


def are_headers_in_model(csv_file_path, model):
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        model_attributes = sorted(
            [
                field.name
                for field in model._meta.fields + model._meta.many_to_many
                if field.name not in {"locked"}
            ]
        )
        headers = sorted(reader.fieldnames)
        uncommon_headers = set(
            model_attributes).symmetric_difference(set(headers))
        if len(uncommon_headers) > 1:
            print(f"Uncommon headers: {uncommon_headers}")
        return len(uncommon_headers) == 1


def load_events():
    with open(DATA_SOURCES[Event], newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            import_context.event_from_dict(row)


def load_demographics():
    with open(DATA_SOURCES[Demographic], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not is_empty(row):
                import_context.responses_from_dict("demographic", row)


def load_qualities():
    with open(DATA_SOURCES[Quality], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not is_empty(row):
                import_context.responses_from_dict("quality", row)


def load_impacts():
    with open(DATA_SOURCES[Impact], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not is_empty(row):
                import_context.responses_from_dict("impact", row)


def load_user():
    with open(DATA_SOURCES[User]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            User.objects.create_user(
                username=row['NodeAccount'],
                password=row['Password']
            )


def load_nodes():
    with open(DATA_SOURCES[Node]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            Node.objects.create(
                name=row['name'],
                country=row['country']
            )


def load_institutions():
    with open(DATA_SOURCES[OrganisingInstitution]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            OrganisingInstitution.objects.create(
                name=row['name'],
            )


def _parse_question_id(value):
    return slugify(value.replace(".", " "))


def load_questions():
    with open(DATA_SOURCES[Question]) as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [
            {
                "question_set": row["slug"].split(".")[0],
                **row,
            }
            for row in reader
        ]
        core_set_name = "TMD Core Questions"
        core_set = QuestionSuperSet.objects.create(
            name=core_set_name,
            slug=slugify(core_set_name),
            user=User.objects.get(username=rows[0]["user"])
        )
        question_sets = {
            set_id: QuestionSet.objects.create(name=set_id, slug=slugify(set_id), user=User.objects.get(username=username))
            for set_id, username in set([(row["question_set"], row["user"]) for row in rows])
        }
        for qs in question_sets.values():
            core_set.question_sets.add(qs)

        for row in rows:
            question_slug = _parse_question_id(row["slug"])
            question_set = question_sets[row["question_set"]]
            question = Question.objects.create(
                slug=question_slug,
                text=row["text"],
                is_multichoice=bool(int(row["is_multichoice"])),
                user=User.objects.get(username=row["user"])
            )
            question_set.questions.add(question)


def load_answers():
    with open(DATA_SOURCES[Answer]) as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            slug = slugify(row["slug"] if row["slug"] else row["text"])
            question_slug = _parse_question_id(row["question"])
            question = Question.objects.get(slug=question_slug)
            Answer.objects.create(
                slug=slug,
                text=row["text"],
                user=User.objects.get(username=row["user"]),
                question=question
            )


def is_empty(items):
    for key, value in items.items():
        if (
            key not in ["user", "created", "updated", "event"]
            and value
        ):
            return False
    return True


class Command(BaseCommand):
    help = 'Load data from CSV files into the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            "--targetdir",
            type=str,
            required=False,
        )

        parser.add_argument(
            "--resetdata",
            action="store_true",
            required=False,
        )

    def handle(self, *args, **options):
        if options["resetdata"]:
            all_models = [
                QuestionSuperSet,
                QuestionSet,
                Question,
                Answer,
                Event,
                Demographic,
                Quality,
                Impact,
                Node,
                OrganisingInstitution,
                User
            ]
            for model in all_models:
                model.objects.all().delete()

        global DATA_SOURCES
        if options["targetdir"]:
            DATA_SOURCES = get_data_sources(options["targetdir"])

        for model, csv_file_path in DATA_SOURCES.items():
            if model == User:
                continue
            if not are_headers_in_model(csv_file_path, model):
                raise Exception(
                    f'Some headers are not present for model {model.__name__} in {csv_file_path}')

        print("LOADING NODES")
        print("------------------------")
        load_nodes()
        print("LOADING INSTITUTIONS")
        print("------------------------")
        load_institutions()
        print("LOADING USERS")
        print("------------------------")
        load_user()
        print("LOADING EVENTS")
        print("------------------------")
        load_events()
        print("LOADING QUESTIONS")
        print("------------------------")
        load_questions()
        print("LOADING ANSWERS")
        print("------------------------")
        load_answers()
        print("LOADING METRICS")
        print("------------------------")

        num_workers = 3
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            functions_to_execute = [
                load_demographics,
                load_qualities,
                load_impacts,
            ]

            futures = [executor.submit(func) for func in functions_to_execute]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"An error occurred: {e}")
