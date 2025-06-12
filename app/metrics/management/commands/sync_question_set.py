from django.core.management.base import BaseCommand
from django.db import transaction
from metrics.models import (
    Answer,
    QuestionSet,
    Question,
    User
)
import json
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Sync a question set. This function assumes your question set "
        "has been fetched from the undocumented Rest API and that the "
        "superset contains only one questionset. "
        "Sets can be found at: https://tmd.elixir-europe.org/properties/set/<supersetid>"
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help='The id of the user')
        parser.add_argument("setid", help='The id of the question set')
        parser.add_argument("filename", help='Path to a question set json file')

    def sync_question_set(self, questionset, data):
        active_questions = {
            question["id"]: question
            for question in data["values"]
        }

        existing_questions = Question.objects.filter(slug__in=list(active_questions.keys()))
        for question in existing_questions:
            logger.info(f"Update question: {question.slug}")
            self.sync_question(question, active_questions[question.slug])

        missing_question_ids = set(active_questions.keys()) - set([q.slug for q in existing_questions])
        for question_id in missing_question_ids:
            logger.info(f"Create question: {question_id}")
            self.create_question(active_questions[question_id])

        all_questions = Question.objects.filter(slug__in=list(active_questions.keys()))
        questionset.questions.set(all_questions)
        questionset.save()

    def create_question(self, data):
        question = Question.create(
            user=self.user,
            text=data["label"],
            slug=data["id"],
        )
        for answer_data in data["options"]:
            answer_slug = answer_data["id"]
            answer_text = answer_data["label"]
            logger.info(f"- {question.slug}:{answer_slug} '{answer_text}' added")
            Answer.objects.create(
                user=self.user,
                question=question,
                text=answer_text,
                slug=answer_slug
            )

    def sync_question(self, question, data):
        active_answers = {
            option["id"]: option
            for option in data["options"]
        }

        existing_answers = question.answers.filter(slug__in=list(active_answers.keys()))
        for answer in existing_answers:
            answer_data = active_answers[answer.slug]
            updated_text = answer_data["label"]
            if answer.text != updated_text:
                logger.info(f"- {question.slug}:{answer.slug} '{answer.text}' -> '{updated_text}'")
                answer.text = updated_text
                answer.save()
            if not answer.is_active:
                logger.info(f"- {question.slug}:{answer.slug} enabled")
                answer.is_active = True
                answer.save()

        answers_to_remove = question.answers.exclude(slug__in=list(active_answers.keys()))
        for answer in answers_to_remove:
            logger.info(f"- {question.slug}:{answer.slug} disabled")
            answer.is_active = False
            answer.save()

        missing_answer_id = set(active_answers.keys()) - set([a.slug for a in existing_answers])
        for answer_id in missing_answer_id:
            answer_data = active_answers[answer_id]
            answer_slug = answer_data["id"]
            answer_text = answer_data["label"]
            logger.info(f"- {question.slug}:{answer_slug} '{answer_text}' added")
            Answer.objects.create(
                user=self.user,
                question=question,
                text=answer_text,
                slug=answer_slug
            )


    def handle(self, *args, filename, setid, username, **options):
        logger.info(f"Updating question set: {setid}")
        with open(filename, "r") as f:
            data = json.load(f)
            questionset = QuestionSet.objects.get(slug=setid)
            self.user = User.objects.get(username=username)
            with transaction.atomic():
                self.sync_question_set(questionset, data)

                should_continue = input("Do you want to continue?")
                if should_continue != "yes":
                    raise RuntimeError("Abort transaction")
