"""
What the public start page shows. Definitions only, no logic.

If questions or answers change (see sync_question_set), update the answer
mappings here. Until then, affected widgets are hidden and a warning is logged.
"""
from .calculations import (
    Average,
    DistinctAnswers,
    Distribution,
    EventCount,
    ResponseCount,
    Share,
)
from .widgets import StackedBars, Stat

MIN_RESPONSES = 30

HERO_STATS = [
    Stat(
        label="training events recorded",
        value=EventCount(),
    ),
    Stat(
        label="participant feedback responses",
        value=ResponseCount(question_sets=("quality", "impact")),
    ),
    Stat(
        label="countries participants work in",
        value=DistinctAnswers(question="demographic-employment_country"),
    ),
    Stat(
        label="would recommend the course",
        value=Share(
            question="quality-recommend_course",
            positive=("yes",),
            negative=("no", "maybe"),
        ),
        value_format="{}%",
        note=Average(
            question="quality-course_rating",
            scores={
                "poor-1": 1,
                "satisfactory-2": 2,
                "good-3": 3,
                "very-good-4": 4,
                "excellent-5": 5,
            },
        ),
        note_format="average rating {:.1f} / 5",
        min_n=MIN_RESPONSES,
    ),
]

# Before and after use the same groups, but the answer slugs differ slightly
# between the two questions ("used" vs "use"), so they are listed separately.
TOOL_USAGE = StackedBars(
    title="From “never used it” to “use it every week”",
    description=(
        "How often participants used the tools covered in the training "
        "before the course, and six months or more after it."
    ),
    min_n=MIN_RESPONSES,
    rows=(
        ("Before training", Distribution(
            question="impact-how_often_use_before",
            groups={
                "Weekly to daily": ("frequently-weekly-to-daily",),
                "Occasionally": ("occasionally-once-in-a-while-to-monthly",),
                "Never": (
                    "never-unaware-of-them",
                    "never-aware-of-them-but-had-not-used-them",
                    "never-used-other-service",
                ),
            },
        )),
        ("After training", Distribution(
            question="impact-how_often_use_after",
            groups={
                "Weekly to daily": ("frequently-weekly-to-daily",),
                "Occasionally": ("occasionally-once-in-a-while-to-monthly",),
                "Never": ("never-use-other-service",),
            },
        )),
    ),
)
