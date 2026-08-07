from metrics.models import (
    Question,
    QuestionSet,
    Answer,
    QuestionSuperSet,
)
from django.contrib.auth.models import User, Permission
from django.template.defaultfilters import slugify
from contextlib import contextmanager


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
    questionset.questions.set(questions)
    questionset.save()
    return questionset


def create_user(username: str, password: str, permissions: list[str] = []):
    new_user = User.objects.create_user(
        username=username,
        password=password,
    )
    for permission_code in permissions:
        permission = Permission.objects.get(codename=permission_code)
        new_user.user_permissions.add(permission)
    new_user.save()
    return new_user



@contextmanager
def with_user_login(client, user):
    try:
        client.force_login(user)
    finally:
        client.logout()


def create_question_data(user):
    question_sets = [
        create_questionset(
            user=user,
            name=set_name,
            slug=slugify(set_name),
            questions=[
                create_question(
                    text=question_name,
                    slug=slugify(f"{set_name}-{question_name}"),
                    user=user,
                    is_multichoice=is_multichoice,
                    choices=[
                        f"{question_name}-{choice}"
                        for choice in ("1", "2", "3")
                    ],
                )
                for question_name, is_multichoice in (
                    ("S1", False),
                    ("S2", False),
                    ("M1", True),
                    ("M2", True),
                )
            ]
        )
        for set_name in ("A", "B", "C", "D")
    ]

    supersets = []
    full_set = QuestionSuperSet.objects.create(
        name="full_set",
        slug="full_set",
        user=user,
        use_for_metrics=True,
        use_for_upload=False,
        is_active=True
    )
    full_set.question_sets.set(question_sets)
    full_set.save()
    supersets.append(full_set)

    for question_set in question_sets:
        superset = QuestionSuperSet.objects.create(
            name=question_set.name,
            slug=question_set.slug,
            user=user,
            use_for_metrics=True,
            use_for_upload=False,
            is_active=True
        )
        superset.question_sets.set([question_set])
        superset.save()
        supersets.append(superset)
    
    return (
        question_sets,
        supersets
    )