from django.test import TestCase
from django.conf import settings
from metrics.models import (
    Node,
    User,
    Event,
)
from metrics.import_utils import ImportContext
import csv
import functools


# Create your tests here.
class TestImportValues(TestCase):
    def test_import_with_aliases(self):
        node = Node.objects.create(name="Test", country="Anywhere")
        user = User.objects.create(username="test")
        event = self._create_event(user, node)

        model_defs = self._read_spec_models()
        context = ImportContext()
        model_import_map = {
            "Event": context.event_from_dict,
            "Demographic": functools.partial(context.responses_from_dict, "demographic"),
            "Quality": functools.partial(context.responses_from_dict, "quality"),
            "Impact": functools.partial(context.responses_from_dict, "impact")
        }
        model_base_data = {
            "Event": {
                "user": user.username,
                "title": "A basic event",
                "node_main": node.name,
                "date_start": "2024-01-01",
                "date_end": "2024-01-02",
                "duration": "2",
                "location_city": "Anytown",
                "location_country": "Sweden",
                "number_participants": "10",
                "number_trainers": "10",
                "url": "https://local.local",
                "organising_institution": "",
                "node": "Test",
            },
            "Demographic": {
                "user": user.username,
                "event": event.code,
                "employment_country": "Sweden",

            },
            "Quality": {
                "user": user.username,
                "event": event.code,
            },
            "Impact": {
                "user": user.username,
                "event": event.code,
            }
        }
        for (model_id, model_def) in model_defs.items():
            model_import = model_import_map[model_id]
            base_data = {
                **model_base_data[model_id],
                **{
                    field_name: values[0]
                    for (field_name, values) in model_def.items()
                }
            }
            for (field_name, values) in model_def.items():
                for value in values:
                    model_import({
                        **base_data,
                        field_name: value
                    })

    def _create_event(self, user, node, title="A test event", code="test"):
        event = Event.objects.create(
            user=user,
            title=title,
            node_main=node,
            date_start="2024-01-01",
            date_end="2024-01-02",
            duration=2,
            location_city="Anytown",
            location_country="Anywhere",
            number_participants=10,
            number_trainers=10,
            funding=["ELIXIR Node"],
            url="https://local.local",
            code=code,
            type="Hackathon",
            target_audience=["Academia/ Research Institution"],
            additional_platforms=["NA"],
            communities=["NA"],
            status="Complete",
        )
        event.node.set([event.id])
        event.save()
        return event

    def _read_spec_models(self):
        aliases_path = getattr(settings, "VALUE_ALIASES_PATH", None)
        if aliases_path:
            fields = {}
            with open(aliases_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    field_id = row["field"]
                    spec_value = row["spec"]
                    if spec_value:
                        fields[field_id] = fields.get(field_id, [])
                        fields[field_id].append(spec_value)
            model_defs = {}
            for (field_id, values) in fields.items():
                [model_id, field_name] = field_id.split(".")
                model_defs[model_id] = model_defs.get(model_id, {})
                model_defs[model_id][field_name] = values
            return model_defs
        else:
            raise RuntimeError("No 'VALUE_ALIASES_PATH' specified")
