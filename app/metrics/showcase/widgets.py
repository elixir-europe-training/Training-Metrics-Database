"""
Widgets: how calculations are shown.

Every widget is a frozen dataclass based on Widget. It knows its calculations,
the template that draws it and the static scripts that template needs. Pages
call render_widget(), which hides the widget when its definition has problems
or there is too little data.

See docs/widgets.md for how these will be reused for Node dashboards.
"""
import logging
from dataclasses import dataclass
from fractions import Fraction
from typing import ClassVar

from .calculations import COUNT_BY_COUNTRY, NODE_PAIRS, NUMBER, PERCENT_BY_GROUP

logger = logging.getLogger(__name__)

PLOTLY = "vendor/plotly-3.0.0-rc.0.min.js"
D3 = "vendor/d3-7.9.0.min.js"

# The widths a widget can have on a dashboard, as a share of the page width
WIDTHS = tuple(Fraction(width) for width in ("1/6", "1/4", "1/3", "1/2", "2/3", "3/4", "5/6", "1"))

HIDDEN_TEMPLATE = "metrics/widgets/hidden.html"


class Hidden(Exception):
    """Raised while building a widget that can't be shown. The message says why."""


@dataclass(frozen=True, kw_only=True)
class Widget:
    """
    Base for all widgets.

    title and description are optional text shown above the widget.
    Calculations based on fewer than min_n data points are treated as missing,
    which hides the widget (or, for a Stat, its note).

    Subclasses set:
        template   the Django template drawing it, which gets the rendered
                   widget as `widget`
        scripts    static files the page must load once
        accepts    the kinds of calculation results it can show (see
                   calculations.py)
        min_width  the smallest width it is readable at (one of WIDTHS)
    and implement build().
    """
    title: str = ""
    description: str = ""
    min_n: int = 0

    template: ClassVar[str] = ""
    scripts: ClassVar[tuple[str, ...]] = ()
    accepts: ClassVar[tuple[str, ...]] = ()
    min_width: ClassVar[Fraction] = Fraction(1, 6)

    @property
    def calculations(self):
        return []

    def check(self):
        """Problems with the definition (empty list = safe to show)."""
        problems = [
            f"{type(self).__name__} can't show {type(calc).__name__} "
            f"({getattr(calc, 'returns', 'unknown')})"
            for calc in self.calculations
            if getattr(calc, "returns", None) not in self.accepts
        ]
        if problems:
            # The calculations' own checks may not apply to the wrong kind
            return problems
        return [problem for calc in self.calculations for problem in calc.check()]

    def calculate(self, calculation, scope):
        """The calculation's value. Raises Hidden if there is none or too little data."""
        result = calculation.calculate(scope)
        if result.value is None:
            raise Hidden("no data")
        if result.n < self.min_n:
            raise Hidden(f"too little data ({result.n} of the {self.min_n} needed)")
        return result.value

    def build(self, scope):
        """The widget-specific template data. Raises Hidden to hide the widget."""
        raise NotImplementedError

    @classmethod
    def widths(cls):
        """The widths this widget type can be given on a dashboard."""
        return [width for width in WIDTHS if width >= cls.min_width]

    @property
    def name(self):
        """Used in log messages."""
        return self.title or type(self).__name__


def _build(widget, scope):
    problems = widget.check()
    if problems:
        logger.warning("Hiding widget '%s': %s", widget.name, "; ".join(problems))
        raise Hidden("; ".join(problems))
    return widget.build(scope)


def render_widget(widget, scope, element_id, show_hidden=False):
    """
    Return the template data for a widget.

    A widget that can't be shown gives None, or with show_hidden (for a
    dashboard's editors) a placeholder saying why, drawn by hidden.html.
    """
    rendered = {
        "id": element_id,
        "data_id": f"{element_id}-data",  # for widgets passing data to a script
        "title": widget.title,
        "description": widget.description,
    }
    try:
        data = _build(widget, scope)
    except Hidden as hidden:
        if not show_hidden:
            return None
        return {**rendered, "template": HIDDEN_TEMPLATE, "scripts": (), "hidden": str(hidden)}
    return {**rendered, "template": widget.template, "scripts": widget.scripts, **data}


def page_scripts(rendered_widgets):
    """The scripts needed by the shown widgets, each once, in order."""
    scripts = {}
    for widget in rendered_widgets:
        if widget is not None:
            scripts.update(dict.fromkeys(widget["scripts"]))
    return list(scripts)


def percent_text(percent):
    return f"{percent:.0f}%"


@dataclass(frozen=True)
class Stat(Widget):
    """
    One big number with a label, optionally with a smaller note, e.g.
    "89%" "would recommend the course" "average rating 4.3 / 5".

    value_format and note_format are normal Python format strings, e.g.
    "{:,}" -> "2,151", "{}%" -> "89%", "average rating {:.1f} / 5".

    Inside a StatGroup only label, value, note and min_n are used.
    """
    label: str
    value: object  # a calculation from calculations.py
    value_format: str = "{:,}"
    note: object | None = None
    note_format: str = ""

    template: ClassVar[str] = "metrics/widgets/stat-card.html"
    accepts: ClassVar[tuple[str, ...]] = (NUMBER,)

    @property
    def calculations(self):
        return [calc for calc in (self.value, self.note) if calc is not None]

    @property
    def name(self):
        return self.title or self.label

    def build(self, scope):
        value = self.calculate(self.value, scope)

        note = None
        if self.note is not None:
            try:
                note = self.note_format.format(self.calculate(self.note, scope))
            except Hidden:
                pass  # the number is still shown, without its note

        return {
            "label": self.label,
            "value": self.value_format.format(value),
            "note": note,
        }


@dataclass(frozen=True)
class StatGroup(Widget):
    """
    Several Stats shown together, as a row of big numbers ("row") or as
    compact tiles ("tiles"). Each Stat is checked and hidden on its own, using
    its own min_n; the group is hidden when none are left.
    """
    stats: tuple[Stat, ...]
    style: str = "row"

    TEMPLATES: ClassVar[dict[str, str]] = {
        "row": "metrics/widgets/stat-row.html",
        "tiles": "metrics/widgets/stat-tiles.html",
    }

    @property
    def template(self):
        return self.TEMPLATES.get(self.style, "")

    def check(self):
        # The stats are checked one by one in build(), so one broken stat
        # doesn't hide the others
        if self.style not in self.TEMPLATES:
            return [f"unknown style '{self.style}'"]
        return []

    def build(self, scope):
        stats, reasons = [], []
        for stat in self.stats:
            try:
                stats.append(_build(stat, scope))
            except Hidden as hidden:
                reasons.append(f"{stat.name}: {hidden}")
        if not stats:
            raise Hidden("; ".join(reasons) or "no stats")
        return {"stats": stats}


@dataclass(frozen=True)
class Bars(Widget):
    """
    One thin bar per group of a Distribution, largest first, e.g. career stages.

    Groups listed in hidden are counted in the total but not drawn, so the
    shown bars can add up to less than 100% (e.g. leaving out "Other").
    """
    value: object  # a Distribution
    hidden: tuple[str, ...] = ()

    template: ClassVar[str] = "metrics/widgets/bars.html"
    accepts: ClassVar[tuple[str, ...]] = (PERCENT_BY_GROUP,)

    @property
    def calculations(self):
        return [self.value]

    def check(self):
        problems = super().check()
        if problems:
            return problems
        unknown = set(self.hidden) - set(self.value.groups)
        if unknown:
            problems.append(f"hidden groups {sorted(unknown)} are not in the distribution")
        return problems

    def build(self, scope):
        bars = [
            {"label": label, "percent": percent, "text": percent_text(percent)}
            for label, percent in self.calculate(self.value, scope).items()
            if label not in self.hidden
        ]
        return {"bars": sorted(bars, key=lambda bar: bar["percent"], reverse=True)}


@dataclass(frozen=True)
class StackedBars(Widget):
    """
    One horizontal bar per row, split into the groups of a Distribution,
    e.g. "Before training" and "After training".

    All rows must use the same group labels. If any row has fewer than min_n
    answers the whole widget is hidden, since the rows are meant to be compared.
    """
    rows: tuple[tuple[str, object], ...]  # (row label, Distribution)

    template: ClassVar[str] = "metrics/widgets/stacked-bars.html"
    accepts: ClassVar[tuple[str, ...]] = (PERCENT_BY_GROUP,)
    min_width: ClassVar[Fraction] = Fraction(1, 4)

    @property
    def calculations(self):
        return [distribution for _, distribution in self.rows]

    def build(self, scope):
        rows = [
            {
                "label": label,
                "segments": [
                    {"label": group, "percent": percent, "text": percent_text(percent)}
                    for group, percent in self.calculate(distribution, scope).items()
                ],
            }
            for label, distribution in self.rows
        ]
        return {
            "legend": [segment["label"] for segment in rows[0]["segments"]],
            "rows": rows,
        }


@dataclass(frozen=True)
class WorldMap(Widget):
    """
    World map coloured by a number per country, e.g. events by country held.
    value is a calculation returning {country name: count}.
    """
    value: object

    template: ClassVar[str] = "metrics/widgets/world-map.html"
    scripts: ClassVar[tuple[str, ...]] = (PLOTLY, "js/world-map.js")
    accepts: ClassVar[tuple[str, ...]] = (COUNT_BY_COUNTRY,)
    min_width: ClassVar[Fraction] = Fraction(1, 3)

    @property
    def calculations(self):
        return [self.value]

    def build(self, scope):
        value = self.calculate(self.value, scope)
        countries = sorted(value)
        return {
            "data": {
                "countries": countries,
                "counts": [value[country] for country in countries],
            },
        }


@dataclass(frozen=True)
class ChordDiagram(Widget):
    """
    Circos/chord diagram of how often Nodes organise courses together, with the
    number of co-organised courses next to it. value is CoOrganisedEvents.
    """
    value: object
    count_label: str = "co-organised courses"

    template: ClassVar[str] = "metrics/widgets/chord.html"
    scripts: ClassVar[tuple[str, ...]] = (D3, "js/chord.js")
    accepts: ClassVar[tuple[str, ...]] = (NODE_PAIRS,)
    min_width: ClassVar[Fraction] = Fraction(1, 3)

    @property
    def calculations(self):
        return [self.value]

    def build(self, scope):
        """
        The pairs are turned into a symmetric matrix, which is what d3.chord
        expects: matrix[i][j] is the number of courses Node i and Node j
        organised together. main[i][j] is the index of the pair's main Node
        (used for the ribbon colour), or None if neither was the main Node.
        """
        value = self.calculate(self.value, scope)
        pairs = value["pairs"]
        nodes = sorted({node for pair in pairs for node in pair})
        index = {node: i for i, node in enumerate(nodes)}
        matrix = [[0] * len(nodes) for _ in nodes]
        main = [[None] * len(nodes) for _ in nodes]
        for (a, b), shared in pairs.items():
            matrix[index[a]][index[b]] = shared
            matrix[index[b]][index[a]] = shared
        for (a, b), node in value["main_nodes"].items():
            main[index[a]][index[b]] = index[node]
            main[index[b]][index[a]] = index[node]

        return {
            "count": f"{value['count']:,}",
            "count_label": self.count_label,
            "data": {"nodes": nodes, "matrix": matrix, "main": main},
        }
