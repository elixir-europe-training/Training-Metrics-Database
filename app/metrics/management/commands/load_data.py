import csv
from metrics.models import Event, Demographic, Quality, Impact, Node, OrganisingInstitution, User
from metrics import import_utils
from django.core.management.base import BaseCommand
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_data_sources(targetdir="example-data"):
    return {
        Event:  f'raw-tmd-data/{targetdir}/tango_events.csv',
        Demographic: f'raw-tmd-data/{targetdir}/tango_demographics.csv',
        Quality: f'raw-tmd-data/{targetdir}/tango_qualities.csv',
        Impact: f'raw-tmd-data/{targetdir}/tango_impacts.csv',
        User: f'raw-tmd-data/{targetdir}/users.csv',
        OrganisingInstitution: f'raw-tmd-data/{targetdir}/institutions.csv',
        Node: f'raw-tmd-data/{targetdir}/nodes.csv'
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
                import_context.demographic_from_dict(row)


def load_qualities():
    with open(DATA_SOURCES[Quality], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not is_empty(row):
                import_context.quality_from_dict(row)


def load_impacts():
    with open(DATA_SOURCES[Impact], newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not is_empty(row):
                import_context.impact_from_dict(row)


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
            )


def load_institutions():
    with open(DATA_SOURCES[OrganisingInstitution]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            OrganisingInstitution.objects.create(
                name=row['name'],
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
            type=str,
            required=False,
        )

    def handle(self, *args, **options):
        if options["resetdata"]:
            all_models = [
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
        print("LOADING METRICS")
        print("------------------------")

        num_workers = 3
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            functions_to_execute = [
                load_demographics, load_qualities, load_impacts]

            futures = [executor.submit(func) for func in functions_to_execute]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"An error occurred: {e}")
