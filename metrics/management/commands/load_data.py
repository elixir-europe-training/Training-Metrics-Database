import csv
from datetime import datetime
from django_countries import countries
from django.utils.text import slugify
from metrics.models import Event, Demographic, Quality, Impact, Node, OrganisingInstitution, User
from django.core.management.base import BaseCommand
from datetime import datetime

events_csv_path = 'raw-tmd-data/example-data/tango_events.csv'
demographics_csv_path = 'raw-tmd-data/example-data/demographics.csv'
qualities_csv_path = 'raw-tmd-data/example-data/qualities_old.csv'
impacts_csv_path = 'raw-tmd-data/example-data/impacts.csv'
users_csv_path = 'raw-tmd-data/example-data/users.csv'
inst_csv_path = 'raw-tmd-data/example-data/institutions.csv'
nodes_csv_path = 'raw-tmd-data/example-data/nodes.csv'


def get_country_code(country_name):
    for code, name in list(countries):
        if name == country_name:
            return code
    return None


def convert_to_timestamp(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').timestamp()


def convert_to_date(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d').date()


def csv_to_array(csv_string):
    return [x for x in csv_string.split(",")] if csv_string else []


def load_events():
    with open(events_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            created = convert_to_timestamp(
                row['created']) if row['created'] else ''
            modified = convert_to_timestamp(
                row['modified']) if row['modified'] else ''

            node_main = row['node_main'] if row['node_main'] else ''

            event = Event.objects.create(
                user=User.objects.get(username=row['user']),
                created=created,
                modified=modified,
                code=slugify(row['code']),
                title=row['title'],
                node_main=Node.objects.get(
                    name=node_main) if node_main else None,
                date_start=convert_to_date(row['date_start']),
                date_end=convert_to_date(row['date_end']),
                duration=float(row['duration']),
                type=row['type'],
                funding=csv_to_array(row['funding']),
                location_city=row['location_city'],
                location_country=row['location_country'],
                target_audience=csv_to_array(row['target_audience']),
                additional_platforms=csv_to_array(row['additional_platforms']),
                communities=csv_to_array(row['communities']),
                number_participants=row['number_participants'],
                number_trainers=row['number_trainers'],
                url=row['url'],
                status=row['status'],
            )
            # event.organising_institution.set([row['organising_institution']])
            node_names = row['node'].split(",")
            stripped_names = [name.strip() for name in node_names]
            nodes = [Node.objects.get(name=node)
                     for node in stripped_names]
            event.node.add(*nodes)

            # Adding ManyToMany relationship with OrganisingInstitution
            # institutions = [OrganisingInstitution.objects.get(
            #    name=inst) for inst in row['organising_institution'].split(",")]
            # event.organising_institution.add(*institutions)


def load_demographics():
    with open(demographics_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            created = convert_to_timestamp(
                row['created']) if row['created'] else ''
            modified = convert_to_timestamp(
                row['modified']) if row['modified'] else ''
            Demographic.objects.create(
                user=User.objects.get(username=row['user']),
                created=created,
                modified=modified,
                event=Event.objects.get(code=int(row['event'])),
                heard_from=csv_to_array(row['heard_from']),
                employment_sector=row['employment_sector'],
                employment_country=get_country_code(row['employment_country']),
                gender=row['gender'],
                career_stage=row['career_stage'],
            )


def load_qualities():
    with open(qualities_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            created = convert_to_timestamp(
                row['created']) if row['created'] else ''
            modified = convert_to_timestamp(
                row['modified']) if row['modified'] else ''
            Quality.objects.create(
                user=User.objects.get(username=row['user']),
                created=created,
                modified=modified,
                event=Event.objects.get(code=row['event']),
                used_resources_before=row['used_resources_before'],
                used_resources_future=row['used_resources_future'],
                recommend_course=row['recommend_course'],
                course_rating=row['course_rating'],
                balance=row['balance'],
                email_contact=row['email_contact'],
            )


def load_impacts():
    with open(impacts_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            created = convert_to_timestamp(
                row['created']) if row['created'] else ''
            modified = convert_to_timestamp(
                row['modified']) if row['modified'] else ''
            Impact.objects.create(
                user=User.objects.get(username=row['user']),
                created=created,
                modified=modified,
                event=Event.objects.get(code=row['event']),
                when_attend_training=row['when_attend_training'],
                main_attend_reason=row['main_attend_reason'],
                how_often_use_before=row['how_often_use_before'],
                how_often_use_after=row['how_often_use_after'],
                able_to_explain=row['able_to_explain'],
                able_use_now=row['able_use_now'],
                help_work=csv_to_array(row['help_work']),
                attending_led_to=csv_to_array(row['attending_led_to']),
                people_share_knowledge=row['people_share_knowledge'],
                recommend_others=row['recommend_others'],
            )


def load_user():
    User.objects.create_user(
        username='tangouser',
        password='tangouser',
    )
    with open(users_csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            User.objects.create_user(
                username=row['NodeAccount'],
                password=row['Password']
            )


def load_nodes():
    with open(nodes_csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            Node.objects.create(
                name=row['name'],
            )


def load_institutions():
    with open(inst_csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            OrganisingInstitution.objects.create(
                name=row['name'],
            )


class Command(BaseCommand):
    help = 'Load data from CSV files into the database.'

    def handle(self, *args, **options):
        Node.objects.all().delete()
        User.objects.all().delete()
        Event.objects.all().delete()
        Demographic.objects.all().delete()
        Quality.objects.all().delete()
        Impact.objects.all().delete()
        OrganisingInstitution.objects.all().delete()
        Node.objects.all().delete()

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
        print("LOADING DEMOGRAPHICS")
        print("------------------------")
        load_demographics()
        print("LOADING QUALITIES")
        print("------------------------")
        load_qualities()
        print("LOADING IMPACTS")
        print("------------------------")
        load_impacts()
