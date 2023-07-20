from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


class Event(models.Model):
    title = models.TextField()
    elixir_node = models.ManyToManyField("ElixirNode")
    date = models.DateField()
    duration = models.DecimalField(max_digits=6, decimal_places=2)
    event_type = models.PositiveIntegerField(
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
    organising_institution = models.TextField()
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
    additional_platforms_involved = models.PositiveIntegerField(
        choices=[
            (1, "Compute"),
            (2, "Data"),
            (3, "Interoperability"),
            (4, "Tools"),
            (5, "NA"),
        ]
    )
    communities_involved = models.PositiveIntegerField(
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
    number_trainer_facilitators = models.PositiveIntegerField()
    event_url = models.URLField()
    short_term_feedback_completed = models.PositiveIntegerField()
    long_term_feedback_completed = models.PositiveIntegerField()
    demographic_entries_completed = models.PositiveIntegerField()
    notes = models.TextField()
    user_id = models.ForeignKey("User", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now=True)
    modified = models.DateTimeField(auto_now=True)


class Demographic(models.Model):
    event_code = models.TextField()
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

    country_employment = models.PositiveIntegerField(
        verbose_name="Country of employment", choices=[
            (1, "TODO: List of countries"),
        ]
    )
    gender = models.PositiveIntegerField(
        choices=[
            (1, "Male"),
            (2, "Female"),
            (3, "Non-binary"),
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
    created_by = models.ForeignKey("User", on_delete=models.CASCADE)


class Feedback(models.Model):
    pass


class DemographicCumFeedback(models.Model):
    pass


class Impact(models.Model):
    pass


class ElixirNode(models.Model):
    name = models.TextField()
    country = CountryField()


class User(AbstractUser):
    pass
