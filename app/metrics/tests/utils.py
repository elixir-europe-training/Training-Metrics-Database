from metrics.models import (
    Question,
    QuestionSet,
    Answer,
)
from django.template.defaultfilters import slugify


def create_question(user, text, slug, choices, is_multichoice=False, choice_slugify=slugify):
    question = Question.objects.create(
        text=text,
        slug=slug,
        user=user,
        is_multichoice=is_multichoice,
    )
    for choice in choices:
        Answer.objects.create(
            question=question,
            text=choice,
            slug=choice_slugify(choice),
            user=user,
        )
    return question


def create_questionset(user, name, slug, questions):
    questionset = QuestionSet.objects.create(
        name=name,
        slug=slug,
        user=user,
    )
    questionset.questions.add(*questions)
    questionset.save()
    return questionset
