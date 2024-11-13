from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
import metrics.models as models


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(
            Submit('submit', 'Log in', css_class='btn btn-dark'))

    username = forms.CharField()

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class QuestionSetForm(forms.Form):
    question_set = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for question in self.question_set.questions.all():
            choices = [
                (answer.slug, answer.text)
                for answer in question.answers.all()
            ]
            label = question.text
            self.fields[question.slug] = (
                forms.MultipleChoiceField(
                    label=label,
                    choices=choices,
                    required=True,
                )
                if question.is_multichoice
                else forms.ChoiceField(
                    label=label,
                    choices=[
                        ("", "---------"),
                        *choices
                    ],
                    required=True,
                )
            )

    def clean(self):
        cleaned_data = super().clean()

        questions = list(self.question_set.questions.all())
        responses = {
            question.slug: question.answers.get(slug=cleaned_data[question.slug])
            for question in questions
            if question.slug in cleaned_data and cleaned_data[question.slug]
        }
        if len(responses) != 0 and len(responses) != len(questions):
            for question in questions:
                if not question.slug in responses:
                    self.add_error(
                        question.slug,
                        ValidationError(f"All responses need to be commited simultaneously"),
                    )

        return responses
    
    @staticmethod
    def from_question_set(qs):
        class _Form(QuestionSetForm):
            question_set = qs

        return _Form

    def save_to(self, response_set):
        if response_set:
            cleaned_data = self.cleaned_data
            question_data = {
                question: cleaned_data[question.slug]
                for question in response_set.question_set.questions.all()
                if cleaned_data[question.slug]
            }

            if len(question_data.keys()) > 0:
                responses = [
                    models.Response(response_set=response_set, answer=question.answers.get(slug=value))
                    for question, data in question_data.items()
                    for value in (data if isinstance(data, list) else [data])
                ]

                for response in responses:
                    response.save()

