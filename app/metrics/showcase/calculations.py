"""
Calculations used by widgets.

Each calculation has two methods:
    check()            -> list of problems with the definition (empty = OK)
    calculate(scope)   -> Result

check() is what keeps widgets safe when questions change: if a question is
removed, or an answer is added/renamed that the definition doesn't know about,
the widget is hidden instead of showing a misleading number.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from django.db.models import Count

from metrics.models import Answer, Event, Question, QuestionSet

NO_RESPONSE = ("no-response",)


@dataclass(frozen=True)
class Result:
    value: float | int | None
    n: int  # number of data points behind the value


def check_question(question_slug, mapped_answers=None):
    """
    Check that the question exists and, if mapped_answers is given, that every
    active answer is mapped and every mapped answer still exists.
    """
    question = Question.objects.filter(slug=question_slug, is_active=True).first()
    if question is None:
        return [f"question '{question_slug}' does not exist or is inactive"]
    if mapped_answers is None:
        return []

    active = set(
        Answer.objects.filter(question=question, is_active=True)
        .values_list("slug", flat=True)
    )
    mapped = set(mapped_answers)
    return [
        *[f"'{question_slug}': answer '{slug}' is not mapped" for slug in sorted(active - mapped)],
        *[f"'{question_slug}': mapped answer '{slug}' no longer exists" for slug in sorted(mapped - active)],
    ]


def count_answers(scope, question_slug):
    """Number of responses per answer slug for one question."""
    rows = (
        scope.responses()
        .filter(answer__question__slug=question_slug)
        .values("answer__slug")
        .annotate(count=Count("id"))
    )
    return {row["answer__slug"]: row["count"] for row in rows}


@dataclass(frozen=True)
class EventCount:
    """Number of events."""

    def check(self):
        return []

    def calculate(self, scope):
        count = scope.events().count()
        return Result(value=count, n=count)


@dataclass(frozen=True)
class EventsByCountry:
    """Number of events per country they were held in, e.g. {"Sweden": 12}."""

    def check(self):
        return []

    def calculate(self, scope):
        rows = (
            scope.events()
            .exclude(location_country__isnull=True)
            .exclude(location_country="")
            .values("location_country")
            .annotate(count=Count("id", distinct=True))
        )
        counts = {row["location_country"]: row["count"] for row in rows}
        if not counts:
            return Result(value=None, n=0)
        return Result(value=counts, n=sum(counts.values()))


@dataclass(frozen=True)
class CoOrganisedEvents:
    """
    Events organised by two or more Nodes, and how often each pair of Nodes
    worked together.

    An event's Nodes are its main Node plus its other Nodes. A course run by
    SE, NL and UK adds one to each pair: SE-NL, SE-UK and NL-UK.

    value is {"count": number of co-organised events,
              "pairs": {(node, node): number of shared events},
              "main_nodes": {(node, node): the pair's Node that was main Node
                             most often (alphabetically first on a tie)}},
    with each pair sorted by name. Pairs where neither Node was ever the main
    Node are not in main_nodes. n is the number of co-organised events.
    """

    def check(self):
        return []

    def calculate(self, scope):
        events = scope.events()
        nodes_per_event = defaultdict(set)
        main_node = {}
        for event_id, name in events.values_list("id", "node_main__name"):
            nodes_per_event[event_id].add(name)
            main_node[event_id] = name
        for event_id, name in Event.node.through.objects.filter(
            event__in=events
        ).values_list("event_id", "node__name"):
            nodes_per_event[event_id].add(name)

        pairs = Counter()
        times_main = defaultdict(Counter)  # pair -> {node: times it was main}
        count = 0
        for event_id, nodes in nodes_per_event.items():
            nodes.discard(None)
            if len(nodes) < 2:
                continue
            count += 1
            for pair in combinations(sorted(nodes), 2):
                pairs[pair] += 1
                if main_node.get(event_id) in pair:
                    times_main[pair][main_node[event_id]] += 1

        if not count:
            return Result(value=None, n=0)
        main_nodes = {
            # max() keeps the first of equal counts, so sorting breaks ties by name
            pair: max(sorted(counts.items()), key=lambda item: item[1])[0]
            for pair, counts in times_main.items()
        }
        return Result(
            value={"count": count, "pairs": dict(pairs), "main_nodes": main_nodes},
            n=count,
        )


@dataclass(frozen=True)
class ResponseCount:
    """Number of filled-in surveys (response sets) for the given question sets."""
    question_sets: tuple[str, ...]

    def check(self):
        existing = set(
            QuestionSet.objects.filter(slug__in=self.question_sets)
            .values_list("slug", flat=True)
        )
        return [
            f"question set '{slug}' does not exist"
            for slug in self.question_sets if slug not in existing
        ]

    def calculate(self, scope):
        count = scope.response_sets().filter(question_set__slug__in=self.question_sets).count()
        return Result(value=count, n=count)


@dataclass(frozen=True)
class DistinctAnswers:
    """Number of different answers given, e.g. number of countries."""
    question: str
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        return check_question(self.question)

    def calculate(self, scope):
        counts = count_answers(scope, self.question)
        given = {slug: count for slug, count in counts.items() if slug not in self.ignored}
        return Result(value=len(given), n=sum(given.values()))


@dataclass(frozen=True)
class AnswerCount:
    """
    Number of participants who picked one specific answer, e.g. how many said
    the training led to a publication. Works for multi-choice questions.

    n is the number of participants who answered the question at all, so
    min_n can hide the number while too few have answered.
    """
    question: str
    answer: str
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        problems = check_question(self.question)
        if not problems and not Answer.objects.filter(
            question__slug=self.question, slug=self.answer, is_active=True
        ).exists():
            problems.append(f"'{self.question}': answer '{self.answer}' no longer exists")
        return problems

    def calculate(self, scope):
        answered = (
            scope.responses()
            .filter(answer__question__slug=self.question)
            .exclude(answer__slug__in=self.ignored)
        )
        count = answered.filter(answer__slug=self.answer).values("response_set").distinct().count()
        n = answered.values("response_set").distinct().count()
        return Result(value=count, n=n)


@dataclass(frozen=True)
class Share:
    """Percentage of answers that are 'positive', out of positive + negative."""
    question: str
    positive: tuple[str, ...]
    negative: tuple[str, ...]
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        return check_question(self.question, [*self.positive, *self.negative, *self.ignored])

    def calculate(self, scope):
        counts = count_answers(scope, self.question)
        positive = sum(counts.get(slug, 0) for slug in self.positive)
        total = positive + sum(counts.get(slug, 0) for slug in self.negative)
        value = round(100 * positive / total) if total else None
        return Result(value=value, n=total)


@dataclass(frozen=True)
class MinimumTotal:
    """
    Lowest possible total for a question answered in ranges, e.g. "How many
    people have you shared your skills with?" with answers 1-5, 6-15, 25+.

    minimums maps every answer to the bottom of its range (0 for "None"), so
    the real total is at least the value. n is the number of answers counted.
    """
    question: str
    minimums: dict[str, int] = field(hash=False)
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        return check_question(self.question, [*self.minimums, *self.ignored])

    def calculate(self, scope):
        counts = count_answers(scope, self.question)
        total = sum(counts.get(slug, 0) for slug in self.minimums)
        if not total:
            return Result(value=None, n=0)
        value = sum(counts.get(slug, 0) * minimum for slug, minimum in self.minimums.items())
        return Result(value=value, n=total)


@dataclass(frozen=True)
class Distribution:
    """
    Percentage of answers in each group, e.g. {"Never": 45.0, "Occasionally": 45.0, ...}.

    groups maps a display label to the answer slugs it includes. The order of
    the groups is the order they are shown in.
    """
    question: str
    groups: dict[str, tuple[str, ...]] = field(hash=False)
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        mapped = [slug for slugs in self.groups.values() for slug in slugs]
        return check_question(self.question, [*mapped, *self.ignored])

    def calculate(self, scope):
        counts = count_answers(scope, self.question)
        group_counts = {
            label: sum(counts.get(slug, 0) for slug in slugs)
            for label, slugs in self.groups.items()
        }
        total = sum(group_counts.values())
        if not total:
            return Result(value=None, n=0)
        return Result(
            value={label: 100 * count / total for label, count in group_counts.items()},
            n=total,
        )


@dataclass(frozen=True)
class Average:
    """Average score, where each answer is given a number, e.g. a 1-5 rating."""
    question: str
    scores: dict[str, float] = field(hash=False)
    ignored: tuple[str, ...] = NO_RESPONSE

    def check(self):
        return check_question(self.question, [*self.scores, *self.ignored])

    def calculate(self, scope):
        counts = count_answers(scope, self.question)
        total = sum(counts.get(slug, 0) for slug in self.scores)
        score_sum = sum(counts.get(slug, 0) * score for slug, score in self.scores.items())
        value = score_sum / total if total else None
        return Result(value=value, n=total)
