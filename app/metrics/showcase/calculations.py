"""
Calculations used by widgets.

Each calculation has two methods:
    check()            -> list of problems with the definition (empty = OK)
    calculate(scope)   -> Result

check() is what keeps widgets safe when questions change: if a question is
removed, or an answer is added/renamed that the definition doesn't know about,
the widget is hidden instead of showing a misleading number.
"""
from dataclasses import dataclass, field

from django.db.models import Count

from metrics.models import Answer, Question, QuestionSet

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
