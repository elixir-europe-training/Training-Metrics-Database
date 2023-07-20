from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


class Event(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    code = models.TextField(unique=True)
    title = models.TextField()
    node = models.ManyToManyField("Node")
    node_main = models.ForeignKey("Node", on_delete=models.CASCADE, related_name='node_main')
    date_start = models.DateField()
    date_end = models.DateField()
    duration = models.DecimalField(max_digits=6, decimal_places=2)
    type = models.PositiveIntegerField(
        choices=[
            (1, "Training - face to face"),
            (2, "Training - e-learning"),
            (3, "Training - blended"),
            (4, "Knowledge Exchange Workshop"),
            (5, "Hackathon"),
        ]
    )
    funding = models.PositiveIntegerField(
        choices=[
            (1, "Converge" "ELIXIR Converge"),
            (2, "EOSC Life"),
            (3, "EXCELLERATE"),
            (4, "ELIXIR Implementation Study"),
            (5, "ELIXIR Community / Use case"),
            (6, "ELIXIR Node"),
            (7, "ELIXIR Hub"),
            (8, "ELIXIR Platform"),
            (9, "Non-ELIXIR / Non-EXCELLERATE Funds"),
        ]
    )
    organising_institution = models.ManyToManyField("OrganisingInstitution")
    location_city = models.TextField()
    location_country = models.PositiveIntegerField(choices=[
        (1, "TODO: List of countries")
    ])
    target_audience = models.PositiveIntegerField(
        choices=[
            (1, "Academia / Research Institution"),
            (2, "Industry"),
            (3, "Non-profit Organisation"),
            (4, "Healthcare"),
        ]
    )
    additional_platforms = models.PositiveIntegerField(
        choices=[
            (1, "Compute"),
            (2, "Data"),
            (3, "Interoperability"),
            (4, "Tools"),
            (5, "NA"),
        ]
    )
    communities = models.PositiveIntegerField(
        choices=[
            (1, "Human Data"),
            (2, "Marine Metagenomics"),
            (3, "Rare Diseases"),
            (4, "Plant Sciences"),
            (5, "Proteomics"),
            (6, "Matabolomics"),
            (7, "Galaxy"),
            (8, "NA"),
        ]
    )
    number_participants = models.PositiveIntegerField()
    number_trainers = models.PositiveIntegerField()
    url = models.URLField()
    status = models.PositiveIntegerField(
        choices=[
            (1, "Complete"),
            (2, "Incomplete"),
        ]
    )


class Demographic(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    heard_from = models.PositiveIntegerField(
        verbose_name="Where did you hear about this course?",
        choices=[
            (1, "TeSS"),
            (2, "Host Institute Website"),
            (3, "Email"),
            (4, "Newsletter"),
            (5, "Colleague"),
            (6, "Internet search"),
            (7, "Other"),
        ],
    )
    employment_sector = models.PositiveIntegerField(
        verbose_name="Employment sector",
        choices=[
            (1, "Academia/ Research Institution"),
            (2, "Industry"),
            (3, "Non-Profit Organisation"),
            (4, "Healthcare"),
            (5, "Other"),
        ],
    )

    employment_country = CountryField()
    gender = models.PositiveIntegerField(
        choices=[
            (1, "Male"),
            (2, "Female"),
            (3, "Other"),
            (4, "Prefer not to say"),
        ]
    )
    career_stage = models.PositiveIntegerField(
        verbose_name="Career stage",
        choices=[
            (1, "Undergraduate student"),
            (2, "Masters student"),
            (3, "PhD candidate"),
            (4, "Postdoctoral researcher"),
            (5, "Senior scientist/ Principal investigator"),
            (6, "Research assistant/ Technician"),
            (7, "Other"),
        ],
    )

class Quality(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    used_resource_before =  models.PositiveIntegerField(
        choices=[
            (1, "Frequently (weekly to daily)"),
            (2, "Occasionally (once in a while to monthly)"),
            (3, "Never - used other service"),
            (4, "Never - aware of them, but not used them"),
            (5, "Never - unaware of them"),
        ]
    )
    used_resources_future = models.PositiveIntegerField(
        choices=[
            (1, "Yes"),
            (2, "No"),
            (3, "Maybe"),
        ]
    )
    reccommend_course =  models.PositiveIntegerField(
        choices=[
            (1, "Yes"),
            (2, "No"),
            (3, "Maybe"),
        ]
    )
    course_rating =  models.PositiveIntegerField(
        choices=[
            (1, "Poor (1)"),
            (2, "Satisfactory (2)"),
            (3, "Good (3)"),
            (4, "Very Good (4)"),
            (5, "Excellent (5)"),
        ]
    )
    balance_choices = [
        (1, "About right"),
        (2, "Too theoretical"),
        (3, "Too practical"),
    ]
    balance = models.PositiveIntegerField(choices=balance_choices)

    email_contact_choices = [
        (1, "Yes"),
        (2, "No"),
    ]
    email_contact = models.PositiveIntegerField(choices=email_contact_choices)



class Impact(models.Model):
    HOW_LONG_CHOICES = [
        (1, "Less than 6 months"),
        (2, "6 months to a year"),
        (3, "Over a year"),
    ]

    REASON_CHOICES = [
        (1, "To learn something new to aid me in my current research/work"),
        (2, "To learn something new for my own interests"),
        (3, "To build on existing knowledge to aid me in my current research/work"),
        (4, "To build on existing knowledge for my own interests"),
        (5, "Other"),
    ]

    HOW_OFTEN_CHOICES = [
        (1, "Never - unaware of them"),
        (2, "Never - aware of them, but had not used them"),
        (3, "Never - used other service"),
        (4, "Occasionally (once in a while to monthly)"),
        (5, "Frequently (weekly to daily)"),
    ]

    EXPLAIN_CHOICES = [
        (1, "Yes"),
        (2, "No"),
        (3, "Maybe"),
        (4, "Other"),
    ]

    ABLE_USE_NOW_CHOICES = [
        (1, "Independently"),
        (2, "By using training materials/notes from the training event"),
        (3, "With the help of an expert"),
        (4, "Other"),
    ]

    ATTENDING_LED_TO_CHOICES = [
        (1, "Authoring of software"),
        (2, "Change in career"),
        (3, "Not applicable"),
        (4, "Other"),
        (5, "Publication of my work"),
        (6, "Submission of a grant application"),
        (7, "Submission of my dissertation/thesis for degree purposes"),
        (8, "Useful collaboration(s) with other participants/trainers from the training event"),
    ]

    PEOPLE_SHARE_KNOWLEDGE_CHOICES = [
        (1, "None"),
        (2, "None yet, but intend to do so in the future"),
        (3, "1-5"),
        (4, "6-15"),
        (5, "16-24"),
        (6, "25+"),
    ]

    RECOMMEND_OTHERS_CHOICES = [
        (1, "Yes, I already have"),
        (2, "Yes, I would"),
        (3, "Maybe"),
        (4, "No"),
    ]

    user = models.ForeignKey("User", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    how_long_ago = models.PositiveIntegerField(choices=HOW_LONG_CHOICES)
    main_attend_reason = models.PositiveIntegerField(choices=REASON_CHOICES)
    how_often_use_after = models.PositiveIntegerField(choices=HOW_OFTEN_CHOICES)
    able_to_explain = models.PositiveIntegerField(choices=EXPLAIN_CHOICES)
    able_use_now = models.PositiveIntegerField(choices=ABLE_USE_NOW_CHOICES)
    attending_led_to = models.PositiveIntegerField(choices=ATTENDING_LED_TO_CHOICES)
    people_share_knowledge = models.PositiveIntegerField(choices=PEOPLE_SHARE_KNOWLEDGE_CHOICES)
    recommend_others = models.PositiveIntegerField(choices=RECOMMEND_OTHERS_CHOICES)

    def __str__(self):
        return f"Attendance: {self.get_how_long_ago_display()}, Reason: {self.get_main_attend_reason_display()}, Use Before: {self.how_often_use_before}, Use After: {self.how_often_use_after}, Able to Explain: {self.able_to_explain}"



class Node(models.Model):
    name = models.TextField()
    country = CountryField()

class OrganisingInstitution(models.Model):
    name = models.TextField()
    country = CountryField()


class User(AbstractUser):
    pass
