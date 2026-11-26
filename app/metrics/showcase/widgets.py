import logging
from dataclasses import dataclass

from django.utils.text import slugify

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stat:
    """
    One big number with a label, optionally with a smaller note below it.

    value_format and note_format are normal Python format strings, e.g.
    "{:,}" -> "2,151", "{}%" -> "89%", "average rating {:.1f} / 5".
    Widgets with fewer than min_n data points are hidden.
    """
    label: str
    value: object  # a calculation from calculations.py
    value_format: str = "{:,}"
    note: object | None = None
    note_format: str = ""
    min_n: int = 0

    @property
    def calculations(self):
        return [calc for calc in (self.value, self.note) if calc is not None]


def problems(widget):
    """All definition problems for a widget (empty list = safe to show)."""
    return [problem for calc in widget.calculations for problem in calc.check()]


def render_stat(stat, scope):
    """
    Return the template data for a Stat, or None if it should be hidden.
    """
    found = problems(stat)
    if found:
        logger.warning("Hiding widget '%s': %s", stat.label, "; ".join(found))
        return None

    value = stat.value.calculate(scope)
    if value.value is None or value.n < stat.min_n:
        return None

    note = None
    if stat.note is not None:
        note_result = stat.note.calculate(scope)
        if note_result.value is not None and note_result.n >= stat.min_n:
            note = stat.note_format.format(note_result.value)

    return {
        "label": stat.label,
        "value": stat.value_format.format(value.value),
        "note": note,
        "n": value.n,
    }


def render_stats(stats, scope):
    """Render a row of Stats, leaving out hidden ones."""
    rendered = [render_stat(stat, scope) for stat in stats]
    return [stat for stat in rendered if stat is not None]


@dataclass(frozen=True)
class Bars:
    """
    One thin bar per group of a Distribution, largest first, e.g. career stages.

    Groups listed in hidden are counted in the total but not drawn, so the
    shown bars can add up to less than 100% (e.g. leaving out "Other").
    """
    title: str
    distribution: object  # a Distribution
    hidden: tuple[str, ...] = ()
    description: str = ""
    source: str = ""
    min_n: int = 0

    def __post_init__(self):
        unknown = set(self.hidden) - set(self.distribution.groups)
        if unknown:
            raise ValueError(f"Bars '{self.title}': hidden groups {sorted(unknown)} are not in the distribution")

    @property
    def calculations(self):
        return [self.distribution]


def render_bars(widget, scope):
    """
    Return the template data for Bars, or None if it should be hidden.
    """
    found = problems(widget)
    if found:
        logger.warning("Hiding widget '%s': %s", widget.title, "; ".join(found))
        return None

    result = widget.distribution.calculate(scope)
    if result.value is None or result.n < widget.min_n:
        return None

    bars = [
        {"label": label, "percent": percent}
        for label, percent in result.value.items()
        if label not in widget.hidden
    ]
    return {
        "title": widget.title,
        "description": widget.description,
        "source": widget.source,
        "n": result.n,
        "bars": sorted(bars, key=lambda bar: bar["percent"], reverse=True),
    }


@dataclass(frozen=True)
class WorldMap:
    """
    World map coloured by a number per country, e.g. events by country held.
    value is a calculation returning {country name: count}.
    """
    title: str
    value: object
    description: str = ""
    source: str = ""
    min_n: int = 0

    @property
    def calculations(self):
        return [self.value]


def render_world_map(widget, scope):
    """
    Return the template data for a WorldMap, or None if it should be hidden.
    """
    found = problems(widget)
    if found:
        logger.warning("Hiding widget '%s': %s", widget.title, "; ".join(found))
        return None

    result = widget.value.calculate(scope)
    if result.value is None or result.n < widget.min_n:
        return None

    countries = sorted(result.value)
    # Unique per widget, so a dashboard can show several maps
    element_id = f"world-map-{slugify(widget.title)}"
    return {
        "id": element_id,
        "data_id": f"{element_id}-data",
        "title": widget.title,
        "description": widget.description,
        "source": widget.source,
        "n": result.n,
        "data": {
            "countries": countries,
            "counts": [result.value[country] for country in countries],
        },
    }


@dataclass(frozen=True)
class ChordDiagram:
    """
    Circos/chord diagram of how often Nodes organise courses together, with the
    number of co-organised courses next to it. value is CoOrganisedEvents.
    """
    title: str
    value: object
    count_label: str = "co-organised courses"
    description: str = ""
    min_n: int = 0

    @property
    def calculations(self):
        return [self.value]


def render_chord_diagram(widget, scope):
    """
    Return the template data for a ChordDiagram, or None if it should be hidden.

    The pairs are turned into a symmetric matrix, which is what d3.chord expects:
    matrix[i][j] is the number of courses Node i and Node j organised together.
    main[i][j] is the index of the pair's main Node (used for the ribbon
    colour), or None if neither was the main Node.
    """
    found = problems(widget)
    if found:
        logger.warning("Hiding widget '%s': %s", widget.title, "; ".join(found))
        return None

    result = widget.value.calculate(scope)
    if result.value is None or result.n < widget.min_n:
        return None

    pairs = result.value["pairs"]
    nodes = sorted({node for pair in pairs for node in pair})
    index = {node: i for i, node in enumerate(nodes)}
    matrix = [[0] * len(nodes) for _ in nodes]
    main = [[None] * len(nodes) for _ in nodes]
    for (a, b), shared in pairs.items():
        matrix[index[a]][index[b]] = shared
        matrix[index[b]][index[a]] = shared
    for (a, b), node in result.value["main_nodes"].items():
        main[index[a]][index[b]] = index[node]
        main[index[b]][index[a]] = index[node]

    element_id = f"chord-{slugify(widget.title)}"
    return {
        "id": element_id,
        "data_id": f"{element_id}-data",
        "title": widget.title,
        "description": widget.description,
        "count": f"{result.value['count']:,}",
        "count_label": widget.count_label,
        "data": {"nodes": nodes, "matrix": matrix, "main": main},
    }


@dataclass(frozen=True)
class StackedBars:
    """
    One horizontal bar per row, split into the groups of a Distribution,
    e.g. "Before training" and "After training".

    All rows must use the same group labels. If any row has fewer than min_n
    answers the whole widget is hidden, since the rows are meant to be compared.
    """
    title: str
    rows: tuple[tuple[str, object], ...]  # (row label, Distribution)
    description: str = ""
    source: str = ""
    min_n: int = 0

    @property
    def calculations(self):
        return [distribution for _, distribution in self.rows]


def render_stacked_bars(widget, scope):
    """
    Return the template data for StackedBars, or None if it should be hidden.
    """
    found = problems(widget)
    if found:
        logger.warning("Hiding widget '%s': %s", widget.title, "; ".join(found))
        return None

    rows = []
    for label, distribution in widget.rows:
        result = distribution.calculate(scope)
        if result.value is None or result.n < widget.min_n:
            return None
        rows.append({
            "label": label,
            "n": result.n,
            "segments": [
                {"label": group, "percent": percent}
                for group, percent in result.value.items()
            ],
        })

    return {
        "title": widget.title,
        "description": widget.description,
        "source": widget.source,
        "legend": [segment["label"] for segment in rows[0]["segments"]],
        "rows": rows,
    }
