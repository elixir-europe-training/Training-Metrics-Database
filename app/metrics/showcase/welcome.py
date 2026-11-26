"""
What the public start page shows. Definitions only, no logic.

If questions or answers change (see sync_question_set), update the answer
mappings here. Until then, affected widgets are hidden and a warning is logged.
"""
from .calculations import (
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
from .widgets import Bars, ChordDiagram, StackedBars, Stat, WorldMap

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

# Each tile counts participants who ticked the answer, not the number of
# publications etc. One participant can tick several answers.
LED_TO_QUESTION = "impact-attending_led_to"

TRAINING_LED_TO = [
    Stat(
        label=label,
        value=AnswerCount(question=LED_TO_QUESTION, answer=answer),
        min_n=MIN_RESPONSES,
    )
    for label, answer in [
        ("publications", "publication-of-my-work"),
        ("useful collaborations", "useful-collaborations-with-other-participants-trainers-from-the-training-event"),
        ("thesis submissions", "submission-of-my-dissertation-thesis-for-degree-purposes"),
        ("authoring softwares", "authoring-of-software"),
        ("grant applications", "submission-of-a-grant-application"),
        ("career changes", "change-in-career"),
    ]
]

# Participants answer in ranges (1-5, 6-15, ...), so the number of colleagues
# is a lower bound: every answer counts as the bottom of its range.
SHARED_WITH_QUESTION = "impact-people_share_knowledge"
SHARED_WITH_MINIMUM = {
    "none": 0,
    "none-yet-but-intend-to-do-so-in-the-future": 0,
    "1-5": 1,
    "6-15": 6,
    "16-24": 16,
    "25": 25,  # "25+"
}

COLLEAGUES_TAUGHT = Stat(
    label="colleagues taught second-hand",
    value=MinimumTotal(question=SHARED_WITH_QUESTION, minimums=SHARED_WITH_MINIMUM),
    value_format="{:,}+",
    note=Share(
        question=SHARED_WITH_QUESTION,
        positive=tuple(slug for slug, minimum in SHARED_WITH_MINIMUM.items() if minimum > 0),
        negative=tuple(slug for slug, minimum in SHARED_WITH_MINIMUM.items() if minimum == 0),
    ),
    note_format="{}% of participants passed their new skills on",
    min_n=MIN_RESPONSES,
)

USE_ON_THEIR_OWN = Stat(
    label="can now use the tools on their own or with the course materials",
    value=Share(
        question="impact-able_use_now",
        positive=(
            "independently",
            "by-using-training-materials-notes-from-the-training-event",
            "with-the-help-of-ai-tools",
        ),
        negative=("with-the-help-of-an-expert", "other"),
    ),
    value_format="{}%",
    min_n=MIN_RESPONSES,
)

WHO_WE_TRAIN = Bars(
    title="Who we train",
    distribution=Distribution(
        question="demographic-career_stage",
        groups={
            "PhD candidates": ("phd-candidate",),
            "Postdocs": ("postdoctoral-researcher",),
            "PIs & senior scientists": ("senior-scientist-principal-investigator",),
            "Master’s & undergraduate students": ("masters-student", "undergraduate-student"),
            "Technical & support staff": ("research-assistant-technician",),
            "Research engineers & staff scientists": (
                "research-engineer-staff-scientist-technical-scientist",
            ),
            "Other": ("other",),
        },
    ),
    # Counted in the percentages, but not shown as a bar
    hidden=("Other",),
    min_n=MIN_RESPONSES,
)

EVENTS_MAP = WorldMap(
    title="Where training events are held",
    description="Number of training events per country, all years.",
    value=EventsByCountry(),
)

NODE_COLLABORATIONS = ChordDiagram(
    title="Training together across Nodes",
    description=(
        "Courses organised jointly by two or more ELIXIR Nodes. Each band is a "
        "Node; each ribbon a shared course, thicker for more courses together."
    ),
    value=CoOrganisedEvents(),
)

ALREADY_RECOMMENDED = Stat(
    label="have already recommended the course to someone else",
    value=Share(
        question="impact-recommend_others",
        positive=("yes-i-already-have",),
        negative=("yes-i-would", "maybe", "no"),
    ),
    value_format="{}%",
    min_n=MIN_RESPONSES,
)
