from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField


class Event(models.Model):
    title = models.TextField()
    elixir_node = models.ForeignKey("ElixirNode", on_delete=models.CASCADE)
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
    location_country = CountryField()
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

    country_employment = CountryField(
        verbose_name="Country of employment"
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
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    frequency_use = models.PositiveIntegerField(
        verbose_name="Have you used the tools/resources before?",
        choices=[
            (1, "Frequently (weekly to daily)"),
            (2, "Occasionally (once in a while to monthly)"),
            (3, "Never - used other service"),
            (4, "Never - aware of them, but not used them"),
            (5, "Never - unaware of them"),
        ]
    )

    future_use = models.PositiveIntegerField(
        verbose_name="Will you use the resources presented in future?",
        choices=[
            (1, "Yes"),
            (2, "No"),
            (3, "Maybe"),
        ]
    )
    recommend = models.PositiveIntegerField(
        verbose_name="Would you recommend this training to others?",
        choices=[
            (1, "Yes, I already have"),
            (2, "Yes, I would"),
            (3, "Maybe"),
            (4, "No"),
        ]
    )
    rating = models.PositiveIntegerField(
        verbose_name="Please tell us your overall rating for the entire course",
        choices=[
            (5, "Excellent (5)"),
            (4, "Very Good (4)"),
            (3, "Good (3)"),
            (2, "Satisfactory (2)"),
            (1, "Poor (1)"),
        ]
    )
    balance = models.PositiveIntegerField(
        verbose_name="Was the balance of material right?",
        choices=[
            (1, "About right"),
            (2, "Too theoretical"),
            (2, "Too practical"),
        ]
    )
    can_contact = models.PositiveIntegerField(
        verbose_name="May we contact you by email in the future for more feeback?",
        choices=[
            (1, "Yes"),
            (2, "No"),
        ]
    )
    enjoy_most = models.TextField(
        verbose_name="What part of the training did you enjoy the most?",
    )
    enjoy_least = models.TextField(
        verbose_name="What part of the training did you enjoy the least?",
    )
    future_topics = models.TextField(
        verbose_name="What other topics would you like to see covered in the future?",
    )
    demographic = models.ForeignKey("Demographic", on_delete=models.CASCADE)


class Impact(models.Model):
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    how_long_ago = models.PositiveIntegerField(
        verbose_name="How long ago did you attend the training?",
        choices=[
            (1, "Less than 6 months"),
            (2, "6 months to a year"),
            (3, "Over a year"),
        ]
    )
    attending_reason = models.PositiveIntegerField(
        verbose_name="What was your main reason for attending the training?",
        choices=[
            (1, "To learn something new to aid me in my current research/ work"),
            (2, "To learn something new for my own interests"),
            (3, "To build on existing knowledge to aid me in my current research/ work"),
            (4, "To build on existing knowledge for my own interests"),
            (5, "Other"),
        ]
    )
    frequency_use_before = models.PositiveIntegerField(
        verbose_name=(
            "How often did you use the tool(s)/resource(s), covered "
            "in the training, BEFORE attending the training?"
        ),
        choices=[
            (1, "Never - unaware of them"),
            (2, "Never - aware of them, but had not used them"),
            (3, "Never - used other service"),
            (4, "Occasionally (once in a while to monthly)"),
            (5, "Frequently (weekly to daily)"),
        ]
    )
    frequency_use_after = models.PositiveIntegerField(
        verbose_name=(
            "How often did you use the tool(s)/resource(s), covered "
            "in the training, AFTER attending the training?"
        ),
        choices=[
            (1, "Never - unaware of them"),
            (2, "Never - aware of them, but had not used them"),
            (3, "Never - used other service"),
            (4, "Occasionally (once in a while to monthly)"),
            (5, "Frequently (weekly to daily)"),
        ]
    )
    can_explain = models.PositiveIntegerField(
        verbose_name="Are you able to explain to others what you learnt in the training?",
        choices=[
            (1, "Yes"),
            (2, "No"),
            (2, "Maybe"),
            (2, "Other"),
        ]
    )
    able_to_use = models.PositiveIntegerField(
        verbose_name="Are you now able to use the tool(s)/resource(s) covered in the training?",
        choices=[
            (1, "Independently"),
            (2, "By using training materials/ notes from the training event"),
            (3, "With the help of an expert"),
            (4, "Other"),
        ]
    )
    how_help = models.PositiveIntegerField(
        verbose_name="How did the training event help with your work?",
        choices=[
            (1, "It did not help as I do not use the tool(s)/resource(s) covered in the training event"),
            (2, "It enabled me to complete certain tasks more quickly"),
            (3, "It has not helped yet but I anticipate a future impact"),
            (4, "It improved communication with the bioinformatician/statistician analyzing my data"),
            (5, "It improved my ability to handle data"),
            (6, "Other"),
        ]
    )
    facilitated = models.PositiveIntegerField(
        verbose_name="Attending the training event led to/facilitated",
        choices=[
            (1, "Authoring of software"),
            (2, "Change in career"),
            (3, "Not applicable"),
            (4, "Other"),
            (5, "Publication of my work"),
            (6, "Submission of a grant application"),
            (7, "Submission of my dissertation/thesis for degree purposes"),
            (8, "Useful collaboration(s) with other participants/trainers from the training event"),
        ]
    )
    number_shared_people = models.PositiveIntegerField(
        verbose_name=(
            "How many people have you shared the skills and/or "
            "knowledge that you learned during the training with?"
        ),
        choices=[
            (1, "None"),
            (2, "None yet, but intend to do so in the future"),
            (3, "1-5"),
            (4, "6-15"),
            (5, "16-24"),
            (6, "25+"),
        ]
    )
    recommend = models.PositiveIntegerField(
        verbose_name="Would you recommend this training to others?",
        choices=[
            (1, "Yes, I already have"),
            (2, "Yes, I would"),
            (3, "Maybe"),
            (4, "No"),
        ]
    )
    created_by = models.ForeignKey("User", on_delete=models.CASCADE)


class ElixirNode(models.Model):
    node_name = models.TextField()
    country = CountryField()


class User(AbstractUser):
    pass
