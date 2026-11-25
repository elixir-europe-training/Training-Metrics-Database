import logging
from dataclasses import dataclass

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
