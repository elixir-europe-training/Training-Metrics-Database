from django.contrib.auth.models import AbstractUser
from django.db import models


class Event(models.Model):
    title = models.TextField()
    elixir_node = models.ForeignKey("ElixirNode")
    date = models.DateField()
    duration = models.DecimalField()
    event_type = models.ChoiceField(
        choices=[
            "Training - face to face",
            "Training - e-learning",
            "Training - blended",
            "Knowledge Exchange Workshop",
            "Hackathon",
        ]
    )
    funding = models.ChoiceField(
        choices=[
            "Converge" "ELIXIR Converge",
            "EOSC Life",
            "EXCELLERATE",
            "ELIXIR Implementation Study",
            "ELIXIR Community / Use case",
            "ELIXIR Node",
            "ELIXIR Hub",
            "ELIXIR Platform",
            "Non-ELIXIR / Non-EXCELLERATE Funds",
        ]
    )
    organising_institution = models.TextField()
    location_city = models.TextField()
    location_country = models.ChoiceField(choices=["TODO: List of countries"])
    excellerate_wp = models.ChoiceField(
        choices=[
            "WP1",
            "WP2",
            "WP3",
            "WP4",
            "WP5",
            "WP6",
            "WP7",
            "WP8",
            "WP9",
            "WP10",
            "WP11 - TeSS",
            "WP11 - Quandl",
            "WP11 - TtT",
            "WP11 - TtR",
            "WP11 - TtD",
        ]
    )
    target_audience = models.ChoiceField(
        choices=[
            "Academia / Research Institution",
            "Industry",
            "Non-profit Organisation",
            "Healthcare",
        ]
    )
    additional_platforms_involved = models.ChoiceField(
        choices=[
            "Compute",
            "Data",
            "Interoperability",
            "Tools",
            "NA",
        ]
    )
    communities_involved = models.ChoiceField(
        choices=[
            "Human Data",
            "Marine Metagenomics",
            "Rare Diseases",
            "Plant Sciences",
            "Proteomics",
            "Matabolomics",
            "Galaxy",
            "NA",
        ]
    )
    number_participants = models.PositiveIntegerField()
    number_trainer_facilitators = models.PositiveIntegerField()
    event_url = models.URLField()
    short_term_feedback_completed = models.PositiveIntegerField()
    long_term_feedback_completed = models.PositiveIntegerField()
    demographic_entries_completed = models.PositiveIntegerField()
    notes = models.TextField()
    user_id = models.ForeignKey("User")
    created = models.DateTimeField(auto_now=True)
    modified = models.DateTimeField(auto_now=True)


class Demographic(models.Model):
    event_code = models.TextField()
    event = models.ForeignKey("Event")
    heard_from = models.ChoiceField(
        verbose_name="Where did you hear about this course?",
        choices=[
            "TeSS",
            "Host Institute Website",
            "Email",
            "Newsletter",
            "Colleague",
            "Internet search",
            "Other",
        ],
    )
    employment_sector = models.ChoiceField(
        verbose_name="Employment sector",
        choices=[
            "Academia/ Research Institution",
            "Industry",
            "Non-Profit Organisation",
            "Healthcare",
            "Other",
        ],
    )

    country_employment = models.ChoiceField(
        verbose_name="Country of employment", choices=["TODO: List of countries"]
    )
    gender = models.ChoiceField(
        choices=[
            "Male",
            "Female",
            "Non-binary",
            "Prefer not to say",
        ]
    )
    career_stage = models.ChoiceField(
        verbose_name="Career stage",
        choices=[
            "Undergraduate student",
            "Masters student",
            "PhD candidate",
            "Postdoctoral researcher",
            "Senior scientist/ Principal investigator",
            "Research assistant/ Technician",
            "Other",
        ],
    )
    created_by = models.ForeignKey("User")


class Feedback(models.Model):
    pass


class DemographicCumFeedback(models.Model):
    pass


class Impact(models.Model):
    pass


class ElixirNode(models.Model):
    pass


class User(AbstractUser):
    pass
