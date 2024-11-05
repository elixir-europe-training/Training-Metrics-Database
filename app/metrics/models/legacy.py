from django.db import models
from .common import ChoiceArrayField, string_choices, EditTracking
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class Demographic(EditTracking):
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="demographic")
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


class Quality(EditTracking):
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="quality")
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


class Impact(EditTracking):
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

    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="impact")
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
