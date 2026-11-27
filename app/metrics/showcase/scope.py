from dataclasses import dataclass
from datetime import date

from metrics.models import Event, Node, Response, ResponseSet
from metrics.views.common import get_event_filter_query


@dataclass(frozen=True)
class Scope:
    """
    Which data a widget is calculated from.

    The start page uses an empty scope (all data). A node dashboard can
    pass a node and/or dates, and every calculation follows along.
    """
    node: Node | None = None
    date_from: date | None = None
    date_to: date | None = None

    def _event_filter(self, prefix=""):
        # Same filter as the event list and metrics pages, so numbers match
        return get_event_filter_query(
            event_node=self.node,
            date_from=self.date_from,
            date_to=self.date_to,
            prefix=prefix,
        )

    def events(self):
        return Event.objects.filter(self._event_filter()).distinct()

    def response_sets(self):
        return ResponseSet.objects.filter(self._event_filter("event__")).distinct()

    def responses(self):
        return Response.objects.filter(
            self._event_filter("response_set__event__")
        ).distinct()
