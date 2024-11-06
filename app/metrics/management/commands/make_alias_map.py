from django.core.management.base import BaseCommand, CommandError

from metrics.models import (
    Event,
    Demographic,
    Quality,
    Impact,
)

class Command(BaseCommand):
    help = "Creates an initial value mapping csv"

    def handle(self, *args, **options):
        models = [
            (Event, ["type", "funding", "target_audience", "additional_platforms", "communities", "status"]),
            (Demographic, ["heard_from", "employment_sector", "gender", "career_stage"]),
            (Quality, ["used_resources_before", "used_resources_future", "recommend_course", "course_rating", "balance", "email_contact"]),
            (Impact, ["when_attend_training", "main_attend_reason", "how_often_use_before", "how_often_use_after", "able_to_explain", "able_use_now", "help_work", "attending_led_to", "people_share_knowledge", "recommend_others"]),
        ]

        print("field,value,alias")
        for (model, fieldIds) in models:
            modelName = model.__name__
            for fieldId in fieldIds:
                choices = model._meta.get_field(fieldId).choices or model._meta.get_field(fieldId).base_field.choices
                if not choices:
                    raise LookupError(f"No options for field {modelName}.{fieldId}")

                values = [
                    (f"{modelName}.{fieldId}", choice)
                    for (choice, _c) in (choices or [])
                ]
                for (valueId, value) in values:
                    print(f'"{valueId}","{value}","{value.lower()}"')