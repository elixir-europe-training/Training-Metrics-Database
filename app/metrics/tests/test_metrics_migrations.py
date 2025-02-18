from metrics.management.commands.migrate_metrics import (
    migrate_entries,
    validate_compatibility,
)
from metrics.models.common import (
    string_choices,
    ChoiceArrayField,
    EditTracking,
    Event,
    Node,
    country_list,
)
from metrics.models import (
    Question,
    QuestionSet,
    Answer,
    Response,
    ResponseSet
)
from django.db import models, connection
from django.test import TestCase
from django.contrib.auth.models import User
import datetime
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError


class TestMetricsA(EditTracking):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    choice_field = models.TextField(
        blank=True,
        choices=string_choices(["A", "B", "C"])
    )
    multichoice_field = ChoiceArrayField(
        base_field=models.TextField(
            blank=True,
            choices=string_choices(["MA", "MB", "MC"])
        )
    )

    class Meta:
        app_label = "tests"


class TestDeviations(EditTracking):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    DEVIATING_CHOICES = [
        *country_list,
        "To learn something new to aid me in my current research/work",  # noqa: E501
        "To build on existing knowledge to aid me in my current research/work",  # noqa: E501
        "By using training materials/notes from the training event",  # noqa: E501
        "It did not help as I do not use the tool(s)/resource(s) covered in the training event",  # noqa: E501
        "It improved communication with the bioinformatician/statistician analyzing my data",  # noqa: E501
        "Submission of my dissertation/thesis for degree purposes",  # noqa: E501
        "Useful collaboration(s) with other participants/trainers from the training event",  # noqa: E501
    ]
    deviations = models.CharField(
        max_length=128,
        choices=string_choices(DEVIATING_CHOICES)
    )


def create_question(user, text, slug, choices, is_multichoice=False):
    question = Question.objects.create(
        text=text,
        slug=slug,
        user=user,
        is_multichoice=is_multichoice,
    )
    for choice in choices:
        Answer.objects.create(
            question=question,
            text=choice,
            slug=slugify(choice),
            user=user,
        )
    return question


def create_questionset(user, name, slug, questions):
    questionset = QuestionSet.objects.create(
        name=name,
        slug=slug,
        user=user,
    )
    questionset.questions.add(*questions)
    questionset.save()
    return questionset


class TestImportValues(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.model_a = TestMetricsA
        cls.model_deviations = TestDeviations
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.model_a)
            schema_editor.create_model(cls.model_deviations)
        cls.user = User.objects.create()
        cls.node = Node.objects.create()
        cls.event_a = Event.objects.create(
            code="123",
            title="Event A",
            date_start=datetime.date.today(),
            date_end=datetime.date.today(),
            duration=1,
            type="Training - face to face",
            location_city="City",
            location_country="Sweden",
            funding=["ELIXIR Converge"],
            target_audience=["Industry"],
            additional_platforms=["Compute"],
            communities=["Human Data"],
            number_participants=4,
            number_trainers=4,
            url="http://localhost",
            status="Complete",
            locked=True,
            node_main=cls.node,
            user=cls.user,
        )
        cls.event_b = Event.objects.create(
            code="234",
            title="Event B",
            date_start=datetime.date.today(),
            date_end=datetime.date.today(),
            duration=1,
            type="Training - face to face",
            location_city="City",
            location_country="Sweden",
            funding=["ELIXIR Converge"],
            target_audience=["Industry"],
            additional_platforms=["Compute"],
            communities=["Human Data"],
            number_participants=4,
            number_trainers=4,
            url="http://localhost",
            status="Complete",
            locked=True,
            node_main=cls.node,
            user=cls.user,
        )

    def setUp(self) -> None:
        self.questionset = create_questionset(
            user=self.user,
            name="TestMetricsA",
            slug="test-metrics-a",
            questions=[
                create_question(
                    text="Choice question",
                    slug="test-metrics-a-choice_field",
                    user=self.user,
                    choices=["A", "B", "C"],
                ),
                create_question(
                    text="Multichoice question",
                    slug="test-metrics-a-multichoice_field",
                    user=self.user,
                    is_multichoice=True,
                    choices=["MA", "MB", "MC"],
                ),
            ]
        )

        self.questionset_deviations = create_questionset(
            user=self.user,
            name="TestDeviations",
            slug="test-deviations",
            questions=[
                create_question(
                    text="Deviations",
                    slug="test-deviations-deviations",
                    user=self.user,
                    choices=[
                        "To learn something new to aid me in my current research / work",  # noqa: E501
                        "To build on existing knowledge to aid me in my current research / work",  # noqa: E501
                        "By using training materials / notes from the training event",  # noqa: E501
                        "It did not help as I do not use the tool(s) / resource(s) covered in the training event",  # noqa: E501
                        "It improved communication with the bioinformatician / statistician analyzing my data",  # noqa: E501
                        "Submission of my dissertation / thesis for degree purposes",  # noqa: E501
                        "Useful collaboration(s) with other participants / trainers from the training event",  # noqa: E501
                        "af",
                        "ec",
                        "lu",
                        "st",
                        "al",
                        "eg",
                        "mk",
                        "sa",
                        "dz",
                        "sv",
                        "mg",
                        "sn",
                        "ad",
                        "gq",
                        "mw",
                        "rs",
                        "ao",
                        "er",
                        "my",
                        "sc",
                        "ag",
                        "ee",
                        "mv",
                        "sl",
                        "ar",
                        "et",
                        "ml",
                        "sg",
                        "am",
                        "fj",
                        "mt",
                        "sk",
                        "au",
                        "fi",
                        "mh",
                        "si",
                        "at",
                        "fr",
                        "mr",
                        "sb",
                        "az",
                        "ga",
                        "mu",
                        "so",
                        "bs",
                        "gm",
                        "mx",
                        "za",
                        "bh",
                        "ge",
                        "fm",
                        "kr",
                        "bd",
                        "de",
                        "md",
                        "ss",
                        "bb",
                        "gh",
                        "mc",
                        "es",
                        "by",
                        "gr",
                        "mn",
                        "lk",
                        "be",
                        "gd",
                        "me",
                        "kn",
                        "bz",
                        "gt",
                        "ma",
                        "lc",
                        "bj",
                        "gn",
                        "mz",
                        "sd",
                        "bt",
                        "gw",
                        "mm",
                        "sr",
                        "bo",
                        "gy",
                        "na",
                        "sz",
                        "ba",
                        "ht",
                        "nr",
                        "se",
                        "bw",
                        "hn",
                        "np",
                        "ch",
                        "br",
                        "hu",
                        "nl",
                        "sy",
                        "bn",
                        "is",
                        "nz",
                        "tw",
                        "bg",
                        "in",
                        "ni",
                        "tj",
                        "bf",
                        "id",
                        "ne",
                        "tz",
                        "bi",
                        "ir",
                        "ng",
                        "th",
                        "kh",
                        "iq",
                        "kp",
                        "tg",
                        "cm",
                        "il",
                        "no",
                        "to",
                        "ca",
                        "it",
                        "om",
                        "tt",
                        "cv",
                        "ci",
                        "other",
                        "tn",
                        "cf",
                        "jm",
                        "pk",
                        "tr",
                        "td",
                        "jp",
                        "pw",
                        "tm",
                        "cl",
                        "jo",
                        "pa",
                        "tv",
                        "cn",
                        "kz",
                        "pg",
                        "ug",
                        "co",
                        "ke",
                        "py",
                        "ua",
                        "km",
                        "ki",
                        "pe",
                        "ae",
                        "cg",
                        "xk",
                        "ph",
                        "gb",
                        "cd",
                        "kw",
                        "pl",
                        "us",
                        "cr",
                        "kg",
                        "pt",
                        "uy",
                        "hr",
                        "la",
                        "qa",
                        "uz",
                        "cu",
                        "lv",
                        "ie",
                        "vu",
                        "cy",
                        "lb",
                        "ro",
                        "va",
                        "cz",
                        "ls",
                        "ru",
                        "ve",
                        "dk",
                        "lr",
                        "rw",
                        "vn",
                        "dj",
                        "ly",
                        "vc",
                        "ye",
                        "dm",
                        "li",
                        "ws",
                        "zm",
                        "do",
                        "lt",
                        "sm",
                        "zw",
                        "tl"
                    ],
                ),
            ]
        )

    def test_validate_compatibility(self):
        validate_compatibility(self.model_a, self.questionset)
        validate_compatibility(
            self.model_deviations,
            self.questionset_deviations
        )

    def test_validate_compatibility_fail_validation_field(self):
        QuestionSet.objects.all().delete()
        Question.objects.all().delete()
        bad_field = create_questionset(
            user=self.user,
            name="BadMetrics",
            slug="test-metrics-a",
            questions=[
                create_question(
                    text="Choice question",
                    slug="test-metrics-a-choice_field",
                    user=self.user,
                    choices=["A", "B", "C"],
                ),
            ]
        )

        try:
            validate_compatibility(self.model_a, bad_field)
        except ValidationError as e:
            self.assertEqual(
                "['Field test-metrics-a-multichoice_field has no representation in set test-metrics-a']",  # noqa: E501
                str(e)
            )

    def test_validate_compatibility_fail_validation_choice(self):
        QuestionSet.objects.all().delete()
        Question.objects.all().delete()
        bad_choice = create_questionset(
            user=self.user,
            name="BadMetrics",
            slug="test-metrics-a",
            questions=[
                create_question(
                    text="Choice question",
                    slug="test-metrics-a-choice_field",
                    user=self.user,
                    choices=["A", "B"],
                ),
                create_question(
                    text="Multichoice question",
                    slug="test-metrics-a-multichoice_field",
                    user=self.user,
                    is_multichoice=True,
                    choices=["MA", "MB", "MC"],
                ),
            ]
        )

        try:
            validate_compatibility(self.model_a, bad_choice)
        except ValidationError as e:
            self.assertEqual(
                "['Choice test-metrics-a-choice_field.C(c) has no representation in set test-metrics-a-choice_field']",  # noqa: E501
                str(e)
            )

    def test_migrate_entries(self):
        self.assertEqual(self.questionset.questions.all().count(), 2)

        variants = [
            (self.event_a, "A", ["MA", "MC"]),
            (self.event_a, "c", ["mA", "Mb"]),
            (self.event_b, "C", ["mb", "mC"]),
            (self.event_b, "b", ["mb", "mC"]),
        ]

        entries = [
            self.model_a.objects.create(
                choice_field=choice,
                multichoice_field=multichoice,
                user=self.user,
                event=event,
            )
            for (event, choice, multichoice) in variants
        ]
        migrate_entries(entries, self.model_a, self.questionset)

        self.assertEquals(
            ResponseSet.objects.filter(event=self.event_a).count(),
            2
        )
        self.assertEquals(
            ResponseSet.objects.filter(event=self.event_b).count(),
            2
        )

        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-choice_field",
                answer__slug="a"
            ).count(),
            1
        )
        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-choice_field",
                answer__slug="b"
            ).count(),
            1
        )
        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-choice_field",
                answer__slug="c"
            ).count(),
            2
        )
        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-multichoice_field",
                answer__slug="ma"
            ).count(),
            2
        )
        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-multichoice_field",
                answer__slug="mb"
            ).count(),
            3
        )
        self.assertEquals(
            Response.objects.filter(
                answer__question__slug="test-metrics-a-multichoice_field",
                answer__slug="mc"
            ).count(),
            3
        )
