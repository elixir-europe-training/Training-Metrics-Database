from metrics.models import Answer
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from .utils import create_questionset, create_question
from django.test import TestCase
from metrics.forms import QuestionSetForm
import itertools


def odd_slugify(value):
    return f"odd-{slugify(value)}"


class TestFormValidation(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(username="user")
        base_questions = {
            f"Choice question {e}": [f"Answer {e}->{i}" for i in range(3)]
            for e in ["A", "B", "C"]
        }
        odd_questions = {
            f"Odd choice question {e}": [f"Answer {e}->{i}" for i in range(3)]
            for e in ["A"]
        }
        self.question_content = {
            **base_questions,
            **odd_questions,
        }

        self.questionset = create_questionset(
            user=self.user,
            name="Test Metrics",
            slug="test-metrics",
            questions=[
                *[
                    create_question(
                        text=question,
                        slug=slugify(question),
                        user=self.user,
                        choices=choices,
                    )
                    for question, choices in base_questions.items()
                ],
                *[
                    create_question(
                        text=question,
                        slug=slugify(question),
                        user=self.user,
                        choices=choices,
                        choice_slugify=odd_slugify
                    )
                    for question, choices in odd_questions.items()
                ]
            ]
        )

        self.multi_choice_question_content = {
            f"Multi choice question {e}": [f"Answer {e}->{i}" for i in range(3)]
            for e in ["A", "B", "C"]
        }
        self.multi_choice_questionset = create_questionset(
            user=self.user,
            name="Test Multi Choice Metrics",
            slug="test-multi-choice-metrics",
            questions=[
                create_question(
                    text=question,
                    slug=slugify(question),
                    user=self.user,
                    choices=choices,
                    is_multichoice=True,
                )
                for question, choices in self.multi_choice_question_content.items()
            ]
        )

    def test_validate_multi_choice_text_responses(self):
        form_class = QuestionSetForm.from_question_set(self.multi_choice_questionset)

        for s in ("|", ","):
            combinations = [[
                (slugify(question), s.join(choices))
                for question, choices in self.multi_choice_question_content.items()
            ]]

            self._assert_combination_validity_status(
                form_class,
                combinations,
                True,
                msg=f"Multi choice can be parsed using '{s}' as separator"
            )

    def test_validate_slug_responses(self):
        form_class = QuestionSetForm.from_question_set(self.questionset)

        all_values = [
            [(slugify(question), slugify(choice)) for choice in choices]
            for question, choices in self.question_content.items()
        ]

        combinations = list(itertools.product(*all_values))
        self._assert_combination_validity_status(
            form_class,
            combinations,
            True
        )

    def test_validate_text_responses(self):
        form_class = QuestionSetForm.from_question_set(self.questionset)
        all_values = [
            [(slugify(question), choice) for choice in choices]
            for question, choices in self.question_content.items()
        ]

        combinations = list(itertools.product(*all_values))
        self._assert_combination_validity_status(
            form_class,
            combinations,
            True
        )

    def test_validate_text_headers(self):
        form_class = QuestionSetForm.from_question_set(self.questionset)
        all_values = [
            [(question, choice) for choice in choices]
            for question, choices in self.question_content.items()
        ]

        combinations = list(itertools.product(*all_values))
        self._assert_combination_validity_status(
            form_class,
            combinations,
            True
        )

    def test_text_responses_to_data(self):
        form_class = QuestionSetForm.from_question_set(self.questionset)
        all_values = [
            [(slugify(question), choice) for choice in choices]
            for question, choices in self.question_content.items()
        ]

        combinations = list(itertools.product(*all_values))
        self.assertTrue(len(combinations) > 0)
        for combination in combinations:
            data = {
                question: choice
                for question, choice in combination
            }
            form = form_class(data)
            self.assertEqual(form.is_valid(), True)
            for key, value in form.cleaned_data.items():
                self.assertTrue(isinstance(value, Answer))
                text = data[key]
                self.assertEqual(text, value.text)

    def test_validate_incorrect_responses(self):
        form_class = QuestionSetForm.from_question_set(self.questionset)
        all_values = [
            [(slugify(question), choice) for choice in ["bad_choice"]]
            for question, _choices in self.question_content.items()
        ]

        combinations = list(itertools.product(*all_values))
        errors = self._assert_combination_validity_status(
            form_class,
            combinations,
            False
        )
        self.assertEqual(
            errors,
            [
                ('choice-question-a', ['Select a valid choice. bad_choice is not one of the available choices.']),
                ('choice-question-b', ['Select a valid choice. bad_choice is not one of the available choices.']),
                ('choice-question-c', ['Select a valid choice. bad_choice is not one of the available choices.']),
                ('odd-choice-question-a', ['Select a valid choice. bad_choice is not one of the available choices.'])
            ]
        )

    def _assert_combination_validity_status(
        self,
        form_class,
        combinations,
        is_valid,
        msg=None
    ):
        self.assertTrue(len(combinations) > 0)
        errors = []
        for combination in combinations:
            data = {
                question: choice
                for question, choice in combination
            }
            form = form_class(data)
            form_is_valid = form.is_valid()
            errors.extend([
                (field, error.messages)
                for field, errors in form.errors.as_data().items()
                for error in errors
            ])
            self.assertEqual(form_is_valid, is_valid, msg=msg)
        return errors
