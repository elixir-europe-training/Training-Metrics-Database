from django.test import TestCase

from metrics.models import Answer, Event, Node, Response, ResponseSet
from metrics.showcase.calculations import (
    AnswerCount,
    Average,
    CoOrganisedEvents,
    DistinctAnswers,
    Distribution,
    EventCount,
    EventsByCountry,
    MinimumTotal,
    ResponseCount,
    Share,
)
from metrics.showcase.scope import Scope
from metrics.showcase.widgets import (
    Bars,
    ChordDiagram,
    StackedBars,
    Stat,
    WorldMap,
    problems,
    render_bars,
    render_chord_diagram,
    render_stacked_bars,
    render_stat,
    render_world_map,
)
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
            question("impact-led_to", ["publication", "software", "not-applicable"]),
            question("impact-shared_with", ["none", "1-5", "25"]),
        ])
        self.shared_with = MinimumTotal(
            question="impact-shared_with",
            minimums={"none": 0, "1-5": 1, "25": 25},
        )
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

    def respond_multichoice(self, event, question_slug, answer_slugs):
        """One participant ticking several answers on a multi-choice question."""
        response_set = ResponseSet.objects.create(user=self.user, event=event, question_set=self.impact)
        for slug in answer_slugs:
            Response.objects.create(
                response_set=response_set,
                answer=Answer.objects.get(question__slug=question_slug, slug=slug),
            )

    def test_answer_count_counts_participants(self):
        event = self.create_event()
        self.respond_multichoice(event, "impact-led_to", ["publication", "software"])
        self.respond_multichoice(event, "impact-led_to", ["publication"])
        self.respond_multichoice(event, "impact-led_to", ["not-applicable"])
        self.respond_multichoice(event, "impact-led_to", ["no-response"])

        publications = AnswerCount(question="impact-led_to", answer="publication").calculate(Scope())
        software = AnswerCount(question="impact-led_to", answer="software").calculate(Scope())

        # n counts everyone who answered, but not those who skipped the question
        self.assertEqual((publications.value, publications.n), (2, 3))
        self.assertEqual((software.value, software.n), (1, 3))

    def test_answer_count_with_removed_answer(self):
        Answer.objects.filter(question__slug="impact-led_to", slug="software").update(is_active=False)

        self.assertEqual(
            AnswerCount(question="impact-led_to", answer="software").check(),
            ["'impact-led_to': answer 'software' no longer exists"],
        )
        self.assertEqual(AnswerCount(question="impact-led_to", answer="publication").check(), [])

    def test_minimum_total_uses_bottom_of_each_range(self):
        event = self.create_event()
        for answer in ("none", "1-5", "1-5", "25", "no-response"):
            self.respond(event, self.impact, {"impact-shared_with": answer})

        result = self.shared_with.calculate(Scope())

        # 0 + 1 + 1 + 25, and the skipped answer is not counted in n
        self.assertEqual((result.value, result.n), (27, 4))

    def test_minimum_total_without_answers_is_hidden(self):
        self.assertIsNone(render_stat(Stat(label="colleagues", value=self.shared_with), Scope()))

    def test_minimum_total_with_unmapped_answer(self):
        minimums = {"none": 0, "1-5": 1}
        self.assertEqual(
            MinimumTotal(question="impact-shared_with", minimums=minimums).check(),
            ["'impact-shared_with': answer '25' is not mapped"],
        )

    def test_stat_card_with_lower_bound_and_note(self):
        event = self.create_event()
        for answer in ("none", "1-5", "25", "25"):
            self.respond(event, self.impact, {"impact-shared_with": answer})
        stat = Stat(
            label="colleagues taught second-hand",
            value=self.shared_with,
            value_format="{:,}+",
            note=Share(question="impact-shared_with", positive=("1-5", "25"), negative=("none",)),
            note_format="{}% passed their skills on",
        )

        rendered = render_stat(stat, Scope())

        self.assertEqual(rendered["value"], "51+")
        self.assertEqual(rendered["note"], "75% passed their skills on")

    def countries(self, **options):
        return Bars(
            title="Countries",
            distribution=Distribution(
                question="demographic-employment_country",
                groups={"Sweden": ("se",), "Norway": ("no",), "Finland": ("fi",)},
            ),
            **options,
        )

    def test_bars_sorted_with_hidden_group_still_counted(self):
        event = self.create_event()
        for country in ("no", "se", "se", "fi", "no-response"):
            self.respond(event, self.demographic, {"demographic-employment_country": country})

        rendered = render_bars(self.countries(hidden=("Finland",)), Scope())

        # Finland is not drawn but is part of the total, so bars sum to 75%
        self.assertEqual(
            [(bar["label"], bar["percent"]) for bar in rendered["bars"]],
            [("Sweden", 50.0), ("Norway", 25.0)],
        )
        self.assertEqual(rendered["n"], 4)

    def test_bars_hidden_below_min_n(self):
        self.respond(self.create_event(), self.demographic, {"demographic-employment_country": "se"})

        self.assertIsNone(render_bars(self.countries(min_n=2), Scope()))

    def test_bars_with_unknown_hidden_group(self):
        with self.assertRaises(ValueError):
            self.countries(hidden=("Denmark",))

    def test_events_by_country(self):
        self.create_event()
        self.create_event()
        Event.objects.filter(pk=self.create_event().pk).update(location_country="Norway")
        Event.objects.filter(pk=self.create_event().pk).update(location_country="")

        result = EventsByCountry().calculate(Scope())

        # Events without a country are left out
        self.assertEqual((result.value, result.n), ({"Sweden": 2, "Norway": 1}, 3))

    def test_world_map_data(self):
        self.create_event()
        Event.objects.filter(pk=self.create_event().pk).update(location_country="Norway")

        rendered = render_world_map(WorldMap(title="Events map", value=EventsByCountry()), Scope())

        self.assertEqual(rendered["id"], "world-map-events-map")
        self.assertEqual(rendered["data"], {"countries": ["Norway", "Sweden"], "counts": [1, 1]})

    def test_world_map_without_events_is_hidden(self):
        self.assertIsNone(render_world_map(WorldMap(title="Map", value=EventsByCountry()), Scope()))

    def test_co_organised_events_counts_every_pair(self):
        third_node = Node.objects.create(name="ELIXIR-UK", country="United Kingdom")
        # Main Node SE plus NO and UK: one course, three pairs
        self.create_event().node.add(self.other_node, third_node)
        # Main Node NO, also listed in its node list: one course, one pair
        self.create_event(self.other_node).node.add(self.node)
        # Only one Node: not co-organised
        self.create_event()

        result = CoOrganisedEvents().calculate(Scope())

        self.assertEqual(result.value["count"], 2)
        self.assertEqual(result.value["pairs"], {
            ("ELIXIR-NO", "ELIXIR-SE"): 2,
            ("ELIXIR-NO", "ELIXIR-UK"): 1,
            ("ELIXIR-SE", "ELIXIR-UK"): 1,
        })
        # NO-SE: each was main once, so the tie goes to NO (first by name).
        # NO-UK: neither was ever main, so it has no main Node.
        self.assertEqual(result.value["main_nodes"], {
            ("ELIXIR-NO", "ELIXIR-SE"): "ELIXIR-NO",
            ("ELIXIR-SE", "ELIXIR-UK"): "ELIXIR-SE",
        })

    def test_co_organised_main_node_is_most_frequent(self):
        for _ in range(2):
            self.create_event().node.add(self.other_node)  # main SE
        self.create_event(self.other_node).node.add(self.node)  # main NO

        result = CoOrganisedEvents().calculate(Scope())

        self.assertEqual(result.value["main_nodes"], {("ELIXIR-NO", "ELIXIR-SE"): "ELIXIR-SE"})

    def test_chord_diagram_matrix(self):
        self.create_event().node.add(self.other_node)

        rendered = render_chord_diagram(ChordDiagram(title="Nodes", value=CoOrganisedEvents()), Scope())

        self.assertEqual(rendered["count"], "1")
        # Main Node SE has index 1 in the sorted Node list
        self.assertEqual(rendered["data"], {
            "nodes": ["ELIXIR-NO", "ELIXIR-SE"],
            "matrix": [[0, 1], [1, 0]],
            "main": [[None, 1], [1, None]],
        })

    def test_chord_diagram_without_co_organised_events_is_hidden(self):
        self.create_event()

        self.assertIsNone(render_chord_diagram(ChordDiagram(title="Nodes", value=CoOrganisedEvents()), Scope()))

    def recommend_question(self):
        return self.quality.questions.get(slug="quality-recommend_course")
