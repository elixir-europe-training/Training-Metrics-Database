from metrics.management.commands.migrate_metrics import (
    dict_to_responseset,
    migrate_entries
)
from metrics.models.common import (
    string_choices,
    ChoiceArrayField,
    EditTracking,
    Event,
    Node,
)
from metrics.models import Question, QuestionSet, Answer
from django.db import models, connection
from django.test import TestCase
from django.apps import apps
from django.contrib.auth.models import User
import datetime
from django.template.defaultfilters import slugify


class TestMetrics(EditTracking):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="testmetrics")
    choice_field = models.TextField(blank=True, choices=string_choices(["A", "B", "C"]))
    multichoice_field = ChoiceArrayField(
        base_field=models.TextField(blank=True, choices=string_choices(["MA", "MB", "MC"]))
    )

    class Meta:
        app_label = "tests"


class TestImportValues(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.model = TestMetrics
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.model)
        cls.user = User.objects.create()
        cls.node = Node.objects.create()
        cls.event = Event.objects.create(
            code="123",
            title="The event",
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

    def test_migrate_entries(self):
        choice_question = Question.objects.create(
            text="Choice question",
            slug="test-metrics-choice_field",
            user=self.user,
        )
        for c_answer in ["A", "B", "C"]:
            Answer.objects.create(
                question=choice_question,
                text=c_answer,
                slug=slugify(c_answer),
                user=self.user,
            )
        multichoice_question = Question.objects.create(
            text="Multichoice question",
            slug="test-metrics-multichoice_field",
            user=self.user,
            is_multichoice=True,
        )
        for mc_answer in ["MA", "MB", "MC"]:
            Answer.objects.create(
                question=multichoice_question,
                text=mc_answer,
                slug=slugify(mc_answer),
                user=self.user,
            )

        questionset = QuestionSet.objects.create(
            name="TestMetrics",
            slug="test-metrics",
            user=self.user,
        )
        questionset.questions.add(
            choice_question,
            multichoice_question,
        )
        questionset.save()

        self.assertEqual(questionset.questions.all().count(), 2)

        variants = [
            ("A", ["MA", "MC"]),
            ("B", ["MA", "MB"]),
            ("C", ["MB", "MC"]),
        ]
        for (choice, multichoice) in variants:
            self.model.objects.create(
                choice_field=choice,
                multichoice_field=multichoice,
                user=self.user,
                event=self.event,
            )

        entries = list(self.model.objects.all())
        migrate_entries(entries, self.model, questionset)

