import csv
from datetime import datetime
from django_countries import countries
from django.utils.text import slugify
from metrics.models import Event, Demographic, Quality, Impact, Node, OrganisingInstitution, User
from django.core.management.base import BaseCommand
from datetime import datetime

# Define the paths to your CSV files
events_csv_path = 'tango_events.csv'
demographics_csv_path = 'demographics.csv'
qualities_csv_path = 'qualities.csv'
impacts_csv_path = 'impacts.csv'
users_csv_path = 'users.csv'


def get_country_code(country_name):
    # Helper function to get the country code from the country name
    for code, name in list(countries):
        if name == country_name:
            return code
    return None


def convert_date_format(date_string):
    try:
        # Parse the input date string using the specified format
        date_object = datetime.strptime(date_string, '%d.%m.%Y')

        # Convert the date object to the desired format
        converted_date = date_object.strftime('%Y-%m-%d')
        return converted_date
    except ValueError:
        raise ValueError(
            "Invalid date format. The input date should be in 'dd.mm.yyyy' format.")


def load_events():
    with open(events_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert date strings to datetime objects
            date_start = datetime.strptime(
                row['date_start'], '%Y-%d-%m').date()
            date_end = datetime.strptime(row['date_end'], '%Y-%m-%d').date()

            # Convert the funding and other fields from CSV to Python lists
            funding = [x for x in row['funding'].split(",")]
            target_audience = [x
                               for x in row['target_audience'].split(",")]
            additional_platforms = [
                x for x in row['additional_platforms'].split(",")]
            communities = [x for x in row['communities'].split(",")]

            # Create the event object and save it to the database
            event = Event.objects.create(
                user=User.objects.get(username=row['user']),
                # Using slugify to generate unique code from the title
                code=slugify(row['code']),
                title=row['title'],
                node_main=Node.objects.get(name=row['node_main']),
                date_start=date_start,
                date_end=date_end,
                duration=float(row['duration']),
                type=row['type'],
                funding=funding,
                location_city=row['location_city'],
                location_country=get_country_code(row['location_country']),
                target_audience=target_audience,
                additional_platforms=additional_platforms,
                communities=communities,
                number_participants=row['number_participants'],
                number_trainers=row['number_trainers'],
                url=row['url'],
                status=row['status'],
            )
            # Adding ManyToMany relationship with Node
            nodes = [Node.objects.get(name=node)
                     for node in row['node'].split(",")]
            event.node.add(*nodes)

            # Adding ManyToMany relationship with OrganisingInstitution
            institutions = [OrganisingInstitution.objects.get(
                name=inst) for inst in row['organising_institution'].split(",")]
            event.organising_institution.add(*institutions)


def load_demographics():
    with open(demographics_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            demographic = Demographic.objects.create(
                user=User.objects.get(username=row['user']),
                event=Event.objects.get(code=row['event']),
                heard_from=[x for x in row['heard_from'].split(",")],
                employment_sector=row['employment_sector'],
                employment_country=get_country_code(row['employment_country']),
                gender=row['gender'],
                career_stage=row['career_stage'],
            )


def load_qualities():
    with open(qualities_csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            quality = Quality.objects.create(
                user=User.objects.get(username=row['user']),
                event=Event.objects.get(code=row['event']),
                used_resource_before=row['used_resource_before'],
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
            impact = Impact.objects.create(
                user=User.objects.get(username=row['user']),
                event=Event.objects.get(code=row['event']),
                when_attend_training=row['when_attend_training'],
                main_attend_reason=row['main_attend_reason'],
                how_often_use_before=row['how_often_use_before'],
                how_often_use_after=row['how_often_use_after'],
                able_to_explain=row['able_to_explain'],
                able_use_now=row['able_use_now'],
                help_work=[x for x in row['help_work'].split(",")],
                attending_led_to=[int(x)
                                  for x in row['attending_led_to'].split(",")],
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


class Command(BaseCommand):
    help = 'Load data from CSV files into the database.'

    def handle(self, *args, **options):
        User.objects.all().delete()
        Event.objects.all().delete()
        Demographic.objects.all().delete()
        Quality.objects.all().delete()
        Impact.objects.all().delete()

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
