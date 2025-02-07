import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from metrics.models import QuestionSet, Quality, Impact, Demographic, ChoiceArrayField
from metrics import metrics_migrations
from django.template.defaultfilters import slugify
from django.db.models import TextField
import difflib



class Command(BaseCommand):
    help = "Migrates metrics from old structure to the new"

    def create_response_map(self):
        response_map = {}
        for Model in [Quality, Impact, Demographic]:
            qs = QuestionSet.objects.filter(slug=Model._meta.verbose_name).get()
            
            for field in Model._meta.get_fields():
                if isinstance(field, TextField) or isinstance(field, ChoiceArrayField):
                    field_id = f"{Model._meta.verbose_name}-{field.name}"
                    question = qs.questions.filter(slug=field_id).get()
                    answers = {
                        answer.slug
                        for answer in question.answers.all()
                    }

                    choices = getattr(field, "choices", [])
                    choices = getattr(
                        getattr(field, "base_field", None),
                        "choices",
                        []
                    ) if not choices else choices
                    for choice, _ in choices:
                        slug_choice = slugify(choice)
                        if slug_choice not in answers:
                            closest_match = difflib.get_close_matches(slug_choice, answers)[0]
                            response_map[slug_choice] = closest_match
                            print(Model._meta.verbose_name, slug_choice, closest_match)
        print(response_map)

    def handle(self, *args, **options):
        (
            quality,
            impact,
            demographic
        ) = (
            QuestionSet.objects.filter(slug=slug).get()
            for slug in ["quality", "impact", "demographic"]
        )

        with transaction.atomic():
            metrics_migrations.quality_to_responseset(list(Quality.objects.all()), quality)
            metrics_migrations.impact_to_responseset(list(Impact.objects.all()), impact)
            metrics_migrations.demographic_to_responseset(list(Demographic.objects.all()), demographic)
