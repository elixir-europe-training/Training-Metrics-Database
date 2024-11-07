from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.urls import reverse
from django import forms
from django.core.exceptions import ValidationError
import re
import requests
from django.contrib.auth.models import User 


def string_choices(choices):
    return [
        (choice, choice)
        for choice in choices
    ]


class ChoiceArrayField(ArrayField):
    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.MultipleChoiceField,
            "choices": self.base_field.choices,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)

class Event(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=128, unique=True, null=True, blank=True)
    title = models.CharField(max_length=1024)
    node = models.ManyToManyField("Node")
    node_main = models.ForeignKey(
        "Node", on_delete=models.CASCADE, related_name='node_main')
    date_start = models.DateField()
    date_end = models.DateField()
    duration = models.DecimalField(verbose_name="Duration (days)", max_digits=6, decimal_places=2)
    type = models.TextField(
        choices=string_choices([
            "Training - face to face",
            "Training - e-learning",
            "Training - blended",
            "Knowledge Exchange Workshop",
            "Hackathon",
        ])
    )
    organising_institution = models.ManyToManyField("OrganisingInstitution")
    location_city = models.CharField(max_length=128)
    location_country = models.CharField(max_length=128)
    funding = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "ELIXIR Converge",
            "EOSC Life",
            "EXCELERATE",
            "ELIXIR Implementation Study",
            "ELIXIR Community / Use case",
            "ELIXIR Node",
            "ELIXIR Hub",
            "ELIXIR Platform",
            "Non-ELIXIR / Non-EXCELERATE Funds",
        ])
    ))


    target_audience = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Academia/ Research Institution",
            "Industry",
            "Non-Profit Organisation",
            "Healthcare",
        ])
    ))

    additional_platforms = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Compute",
            "Data",
            "Interoperability",
            "Tools",
            "NA",
        ])
    ))

    communities = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Human Data",
            "Marine Metagenomics",
            "Rare Diseases",
            "Plant Sciences",
            "Proteomics",
            "Metabolomics",
            "Galaxy",
            "NA",
        ])
    ))

    number_participants = models.PositiveIntegerField()
    number_trainers = models.PositiveIntegerField()
    url = models.URLField(max_length=4096)
    status = models.TextField(
        choices=string_choices([
            "Complete",
            "Incomplete",
        ])
    )
    locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.id}) ({self.code})"
    

    def get_absolute_url(self):
        return reverse("event-edit", kwargs={"pk": self.id})
    

    @property
    def location(self):
        return (
            self.location_city,
            self.location_country
        )
    
    @property
    def date_period(self):
        return (
            self.date_start,
            self.date_end
        )

    @property
    def stats(self):
        return [
            (name, model.objects.filter(event=self).count())
            for name, model in [
                ("Quality metrics", Quality),
                ("Impact metrics", Impact),
                ("Demographic metrics", Demographic)
            ]
        ]

    @property
    def metrics_status(self):
        count = sum([1 if v > 0 else 0 for _n, v in self.stats])
        return {
            0: "None",
            1: "Partial",
            2: "Partial",
            3: "Full"
        }[count]
    
    @property
    def is_locked(self):
        return (
            self.code is not None
            or self.locked
        )


class Demographic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    employment_country = models.TextField(blank=True)
    heard_from = ChoiceArrayField(base_field=models.TextField(
            choices=string_choices([
                "TeSS",
                "Host Institute Website",
                "Email",
                "Newsletter",
                "Colleague",
                "Internet search",
                "Other",
            ]),
        ),
        verbose_name="Where did you hear about this course?",
    )

    employment_sector = models.TextField(
        verbose_name="Employment sector",
        choices=[
            ("Academia/ Research Institution", "Academia/ Research Institution"),
            ("Industry", "Industry"),
            ("Non-Profit Organisation", "Non-Profit Organisation"),
            ("Healthcare", "Healthcare"),
            ("Other", "Other"),
        ],
    )

    gender = models.TextField(
        choices=[
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other"),
            ("Prefer not to say", "Prefer not to say"),
        ]
    )

    career_stage = models.TextField(
        verbose_name="Career stage",
        choices=[
            ("Undergraduate student", "Undergraduate student"),
            ("Masters student", "Masters student"),
            ("PhD candidate", "PhD candidate"),
            ("Postdoctoral researcher", "Postdoctoral researcher"),
            ("Senior scientist/ Principal investigator",
             "Senior scientist/ Principal investigator"),
            ("Research assistant/ Technician", "Research assistant/ Technician"),
            ("Other", "Other"),
        ],
    )


class Quality(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    used_resources_before = models.TextField(
        blank=True,
        choices=[
            ("Frequently (weekly to daily)", "Frequently (weekly to daily)"),
            ("Occasionally (once in a while to monthly)",
             "Occasionally (once in a while to monthly)"),
            ("Never - used other service", "Never - used other service"),
            ("Never - aware of them, but not used them",
             "Never - aware of them, but not used them"),
            ("Never - unaware of them", "Never - unaware of them"),
        ]
    )

    used_resources_future = models.TextField(
        blank=True,
        choices=[
            ("Yes", "Yes"),
            ("No", "No"),
            ("Maybe", "Maybe"),
        ]
    )

    recommend_course = models.TextField(
        blank=True,
        choices=[
            ("Yes", "Yes"),
            ("No", "No"),
            ("Maybe", "Maybe"),
        ]
    )

    course_rating = models.TextField(
        blank=True,
        choices=[
            ("Poor (1)", "Poor (1)"),
            ("Satisfactory (2)", "Satisfactory (2)"),
            ("Good (3)", "Good (3)"),
            ("Very Good (4)", "Very Good (4)"),
            ("Excellent (5)", "Excellent (5)"),
        ]
    )

    balance_choices = [
        ("About right", "About right"),
        ("Too theoretical", "Too theoretical"),
        ("Too practical", "Too practical"),
    ]

    balance = models.TextField(
        blank=True,
        choices=[
            ("About right", "About right"),
            ("Too theoretical", "Too theoretical"),
            ("Too practical", "Too practical"),
        ]
    )

    email_contact = models.TextField(
        choices=[
            ("Yes", "Yes"),
            ("No", "No"),
        ]
    )


class Impact(models.Model):
    HOW_LONG_CHOICES = [
        ("Less than 6 months", "Less than 6 months"),
        ("6 months to a year", "6 months to a year"),
        ("Over a year", "Over a year"),
    ]

    REASON_CHOICES = [
        ("To learn something new to aid me in my current research/work",
         "To learn something new to aid me in my current research/work"),
        ("To learn something new for my own interests",
         "To learn something new for my own interests"),
        ("To build on existing knowledge to aid me in my current research/work",
         "To build on existing knowledge to aid me in my current research/work"),
        ("To build on existing knowledge for my own interests",
         "To build on existing knowledge for my own interests"),
        ("Other", "Other"),
    ]

    HOW_OFTEN_BEFORE_CHOICES = [
        ("Never - unaware of them", "Never - unaware of them"),
        ("Never - aware of them, but had not used them",
         "Never - aware of them, but had not used them"),
        ("Never - used other service", "Never - used other service"),
        ("Occasionally (once in a while to monthly)",
         "Occasionally (once in a while to monthly)"),
        ("Frequently (weekly to daily)", "Frequently (weekly to daily)"),
    ]

    HOW_OFTEN_AFTER_CHOICES = [
        ("Never - use other service", "Never - use other service"),
        ("Occasionally (once in a while to monthly)",
         "Occasionally (once in a while to monthly)"),
        ("Frequently (weekly to daily)", "Frequently (weekly to daily)"),
    ]

    EXPLAIN_CHOICES = [
        ("Yes", "Yes"),
        ("No", "No"),
        ("Maybe", "Maybe"),
        ("Other", "Other"),
    ]

    ABLE_USE_NOW_CHOICES = [
        ("Independently", "Independently"),
        ("By using training materials/notes from the training event",
         "By using training materials/notes from the training event"),
        ("With the help of an expert", "With the help of an expert"),
        ("Other", "Other"),
    ]

    ATTENDING_LED_TO_CHOICES = [
        ("Authoring of software", "Authoring of software"),
        ("Change in career", "Change in career"),
        ("Not applicable", "Not applicable"),
        ("Other", "Other"),
        ("Publication of my work", "Publication of my work"),
        ("Submission of a grant application", "Submission of a grant application"),
        ("Submission of my dissertation/thesis for degree purposes",
         "Submission of my dissertation/thesis for degree purposes"),
        ("Useful collaboration(s) with other participants/trainers from the training event",
         "Useful collaboration(s) with other participants/trainers from the training event"),
    ]

    PEOPLE_SHARE_KNOWLEDGE_CHOICES = [
        ("None", "None"),
        ("None yet, but intend to do so in the future",
         "None yet, but intend to do so in the future"),
        ("1-5", "1-5"),
        ("6-15", "6-15"),
        ("16-24", "16-24"),
        ("25+", "25+"),
    ]

    RECOMMEND_OTHERS_CHOICES = [
        ("Yes, I already have", "Yes, I already have"),
        ("Yes, I would", "Yes, I would"),
        ("Maybe", "Maybe"),
        ("No", "No"),
    ]

    HELP_WORK_CHOICES = [
        ("It did not help as I do not use the tool(s)/resource(s) covered in the training event",
         "It did not help as I do not use the tool(s)/resource(s) covered in the training event"),
        ("It enabled me to complete certain tasks more quickly",
         "It enabled me to complete certain tasks more quickly"),
        ("It has not helped yet but I anticipate a future impact",
         "It has not helped yet but I anticipate a future impact"),
        ("It improved communication with the bioinformatician/statistician analyzing my data",
         "It improved communication with the bioinformatician/statistician analyzing my data"),
        ("It improved my ability to handle data",
         "It improved my ability to handle data"),
        ("Other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    when_attend_training = models.TextField(
        choices=HOW_LONG_CHOICES)
    main_attend_reason = models.TextField(blank=True, choices=REASON_CHOICES)
    how_often_use_before = models.TextField(
        blank=True,
        choices=HOW_OFTEN_BEFORE_CHOICES)
    how_often_use_after = models.TextField(
        blank=True,
        choices=HOW_OFTEN_AFTER_CHOICES)
    able_to_explain = models.TextField(choices=EXPLAIN_CHOICES)
    able_use_now = models.TextField(choices=ABLE_USE_NOW_CHOICES)
    help_work = ChoiceArrayField(
        base_field=models.TextField(choices=HELP_WORK_CHOICES)
    )
    attending_led_to = ChoiceArrayField(
        blank=True,
        base_field=models.TextField(choices=ATTENDING_LED_TO_CHOICES)
    )
    people_share_knowledge = models.TextField(
        blank=True,
        choices=PEOPLE_SHARE_KNOWLEDGE_CHOICES)
    recommend_others = models.TextField(
        blank=True,
        choices=RECOMMEND_OTHERS_CHOICES)

    def __str__(self):
        return f"Attendance: {self.get_how_long_ago_display()}, Reason: {self.get_main_attend_reason_display()}, Use Before: {self.how_often_use_before}, Use After: {self.how_often_use_after}, Able to Explain: {self.able_to_explain}"


class Node(models.Model):
    name = models.TextField()
    country = models.TextField()

    def __str__(self):
        return (
            f"{self.name} ({self.country})"
            if self.country
            else self.name
        )


def is_ror_id(value):
    if re.match("^https://ror.org/[a-zA-Z0-9]+$", value):
        return value
    raise ValidationError(f"Not a valid ror id: {value}")


class OrganisingInstitution(models.Model):
    name = models.TextField()
    country = models.TextField()
    ror_id = models.URLField(max_length=512, unique=True, null=True, validators=[is_ror_id])

    def __str__(self):
        return (
            f"{self.name} ({self.country})"
            if self.country
            else str(self.name)
        )

    def get_absolute_url(self):
        return reverse("institution-edit", kwargs={"pk": self.id})

    def update_ror_data(self):
        try:
            ror_id_base = re.match("^https://ror.org/(.+)$", self.ror_id)[0]
            ror_url = f"https://api.ror.org/organizations/{ror_id_base}"
            response = requests.get(ror_url, allow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                self.name = data["name"]
                self.country = data.get("country", {}).get("country_name", "")
            else:
                raise ValidationError(f"Could not fetch ROR data for: {self.ror_id}, {ror_url}, {response.status_code}")
        except TypeError:
            raise ValidationError(f"Not a valid ror id: {self.ror_id}")


def get_node(self):
    node_name = f"ELIXIR-{self.username.upper()}"
    try:
        return Node.objects.get(name=node_name)
    except Node.DoesNotExist:
        return None

User.add_to_class("get_node", get_node)
