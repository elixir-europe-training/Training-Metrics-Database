from django.test import TestCase

from metrics.models import Answer, Event, Node, Response, ResponseSet
from metrics.showcase.calculations import (
    Average,
    DistinctAnswers,
    Distribution,
    EventCount,
    ResponseCount,
    Share,
)
from metrics.showcase.scope import Scope
from metrics.showcase.widgets import StackedBars, Stat, problems, render_stacked_bars, render_stat
from .utils import create_question, create_questionset, create_user

RATINGS = {"poor-1": 1, "satisfactory-2": 2, "good-3": 3, "very-good-4": 4, "excellent-5": 5}


class TestShowcase(TestCase):
    def setUp(self):
        self.user = create_user("admin", "pwd")
        self.node = Node.objects.create(name="ELIXIR-SE", country="Sweden")
        self.other_node = Node.objects.create(name="ELIXIR-NO", country="Norway")

        def question(slug, answers):
            return create_question(
                self.user, slug, slug, ["no-response", *answers],
                choice_slugify=lambda choice: choice,
            )

        self.quality = create_questionset(self.user, "Quality", "quality", [
            question("quality-recommend_course", ["yes", "no", "maybe"]),
            question("quality-course_rating", list(RATINGS)),
        ])
        self.demographic = create_questionset(self.user, "Demographic", "demographic", [
            question("demographic-employment_country", ["se", "no", "fi"]),
        ])
        self.impact = create_questionset(self.user, "Impact", "impact", [
            question("impact-use_before", ["weekly", "monthly", "never"]),
            question("impact-use_after", ["weekly", "monthly", "never"]),
        ])
        usage_groups = {"Weekly": ("weekly",), "Monthly": ("monthly",), "Never": ("never",)}
        self.usage = StackedBars(
            title="Tool usage",
            rows=(
                ("Before", Distribution(question="impact-use_before", groups=usage_groups)),
                ("After", Distribution(question="impact-use_after", groups=usage_groups)),
            ),
            min_n=4,
        )

        self.recommend = Share(
            question="quality-recommend_course",
            positive=("yes",),
            negative=("no", "maybe"),
        )
        self.rating = Average(question="quality-course_rating", scores=RATINGS)

    def create_event(self, node=None):
        node = node or self.node
        event = Event.objects.create(
            user=self.user,
            title="Event",
            node_main=node,
            date_start="2026-01-01",
            date_end="2026-01-02",
            duration=2,
            type="Training - face to face",
            location_city="Uppsala",
            location_country="Sweden",
            funding=["ELIXIR Node"],
            target_audience=["Academia/ Research Institution"],
            additional_platforms=["Compute"],
            communities=["NA"],
            number_participants=10,
            number_trainers=2,
            url="http://test.local",
            status="Complete",
        )
        event.node.add(node)
        return event

    def respond(self, event, question_set, answers, times=1):
        """Add `times` survey responses with the given {question: answer} pairs."""
        for _ in range(times):
            response_set = ResponseSet.objects.create(
                user=self.user, event=event, question_set=question_set
            )
            for question_slug, answer_slug in answers.items():
                Response.objects.create(
                    response_set=response_set,
                    answer=Answer.objects.get(question__slug=question_slug, slug=answer_slug),
                )

    def test_counts(self):
        event = self.create_event()
        self.create_event()
        self.respond(event, self.quality, {"quality-recommend_course": "yes"}, times=3)
        self.respond(event, self.demographic, {"demographic-employment_country": "se"})

        self.assertEqual(EventCount().calculate(Scope()).value, 2)
        self.assertEqual(ResponseCount(question_sets=("quality",)).calculate(Scope()).value, 3)

    def test_distinct_answers_ignores_no_response(self):
        event = self.create_event()
        for country in ("se", "se", "no", "no-response"):
            self.respond(event, self.demographic, {"demographic-employment_country": country})

        result = DistinctAnswers(question="demographic-employment_country").calculate(Scope())

        self.assertEqual(result.value, 2)
        self.assertEqual(result.n, 3)

    def test_share_and_average(self):
        event = self.create_event()
        self.respond(event, self.quality, {"quality-recommend_course": "yes", "quality-course_rating": "excellent-5"}, times=3)
        self.respond(event, self.quality, {"quality-recommend_course": "maybe", "quality-course_rating": "good-3"})
        self.respond(event, self.quality, {"quality-recommend_course": "no-response", "quality-course_rating": "no-response"})

        share = self.recommend.calculate(Scope())
        average = self.rating.calculate(Scope())

        self.assertEqual((share.value, share.n), (75, 4))
        self.assertEqual((average.value, average.n), (4.5, 4))

    def test_scope_limits_to_node(self):
        self.respond(self.create_event(), self.quality, {"quality-recommend_course": "yes"})
        self.respond(self.create_event(self.other_node), self.quality, {"quality-recommend_course": "no"})

        self.assertEqual(self.recommend.calculate(Scope(node=self.node)).value, 100)
        self.assertEqual(self.recommend.calculate(Scope()).value, 50)
        self.assertEqual(EventCount().calculate(Scope(node=self.other_node)).value, 1)

    def test_definitions_without_problems(self):
        self.assertEqual(problems(Stat(label="x", value=self.recommend, note=self.rating)), [])

    def test_new_answer_hides_widget(self):
        """The sync_question_set case: a new answer appears that isn't mapped yet."""
        Answer.objects.create(
            question=self.recommend_question(), text="Not sure", slug="not-sure", user=self.user,
        )
        stat = Stat(label="would recommend", value=self.recommend)

        self.assertEqual(problems(stat), ["'quality-recommend_course': answer 'not-sure' is not mapped"])
        with self.assertLogs("metrics.showcase.widgets", level="WARNING"):
            self.assertIsNone(render_stat(stat, Scope()))

    def test_renamed_answer_hides_widget(self):
        Answer.objects.filter(question=self.recommend_question(), slug="maybe").update(is_active=False)

        self.assertIn(
            "'quality-recommend_course': mapped answer 'maybe' no longer exists",
            problems(Stat(label="x", value=self.recommend)),
        )

    def test_missing_question_hides_widget(self):
        stat = Stat(label="x", value=DistinctAnswers(question="does-not-exist"))

        with self.assertLogs("metrics.showcase.widgets", level="WARNING"):
            self.assertIsNone(render_stat(stat, Scope()))

    def test_render_stat(self):
        event = self.create_event()
        self.respond(event, self.quality, {"quality-recommend_course": "yes", "quality-course_rating": "very-good-4"}, times=9)
        self.respond(event, self.quality, {"quality-recommend_course": "no", "quality-course_rating": "good-3"})
        stat = Stat(
            label="would recommend the course",
            value=self.recommend,
            value_format="{}%",
            note=self.rating,
            note_format="average rating {:.1f} / 5",
            min_n=10,
        )

        self.assertEqual(render_stat(stat, Scope()), {
            "label": "would recommend the course",
            "value": "90%",
            "note": "average rating 3.9 / 5",
            "n": 10,
        })

    def test_too_few_responses_hides_widget(self):
        self.respond(self.create_event(), self.quality, {"quality-recommend_course": "yes"}, times=5)

        self.assertIsNone(render_stat(Stat(label="x", value=self.recommend, min_n=10), Scope()))

    def test_distribution(self):
        event = self.create_event()
        for answer in ("weekly", "monthly", "monthly", "never", "no-response"):
            self.respond(event, self.impact, {"impact-use_before": answer})

        result = Distribution(
            question="impact-use_before",
            groups={"Used": ("weekly", "monthly"), "Never": ("never",)},
        ).calculate(Scope())

        self.assertEqual(result.value, {"Used": 75, "Never": 25})
        self.assertEqual(result.n, 4)

    def test_render_stacked_bars(self):
        event = self.create_event()
        for before, after in [("never", "weekly"), ("never", "weekly"), ("monthly", "monthly"), ("weekly", "weekly")]:
            self.respond(event, self.impact, {"impact-use_before": before, "impact-use_after": after})

        widget = render_stacked_bars(self.usage, Scope())

        self.assertEqual(widget["legend"], ["Weekly", "Monthly", "Never"])
        self.assertEqual(
            [(row["label"], row["n"], [segment["percent"] for segment in row["segments"]]) for row in widget["rows"]],
            [("Before", 4, [25, 25, 50]), ("After", 4, [75, 25, 0])],
        )

    def test_stacked_bars_hidden_when_one_row_has_too_few_answers(self):
        event = self.create_event()
        self.respond(event, self.impact, {"impact-use_before": "never"}, times=4)
        self.respond(event, self.impact, {"impact-use_after": "weekly"}, times=3)

        self.assertIsNone(render_stacked_bars(self.usage, Scope()))

    def test_stacked_bars_hidden_when_answer_not_mapped(self):
        Answer.objects.create(
            question=self.impact.questions.get(slug="impact-use_after"),
            text="Daily", slug="daily", user=self.user,
        )

        with self.assertLogs("metrics.showcase.widgets", level="WARNING"):
            self.assertIsNone(render_stacked_bars(self.usage, Scope()))

    def recommend_question(self):
        return self.quality.questions.get(slug="quality-recommend_course")
