from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from metrics import models
from django.forms import ModelForm
from django.forms.widgets import CheckboxInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(
            Submit('submit', 'Log in', css_class='btn btn-dark'))

    username = forms.CharField()

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class MetricsFilterForm(ModelForm):
    class Meta:
         model = models.Event
         fields = [
            "date_start",
            "date_end",
            "type",
            "funding",
            "target_audience",
            "additional_platforms"
         ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

        self.helper = FormHelper(self)
        self.helper.form_method = "GET"
        self.helper.form_class = "row"
        self.helper.wrapper_class = "col-lg-4"
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            Field("date_start", css_class="datepicker form-control"),
            Field("date_end", css_class="datepicker form-control"),
            "type",
            "funding",
            "target_audience",
            "additional_platforms",
            Div(css_class="col-lg-10"),
            Submit("submit", 'Filter', css_class="col-lg-2"),
        )



class QuestionSetForm(forms.Form):
    question_set = None

    def __init__(self, values, *args, **kwargs):
        fields = {
            question.slug: QuestionSetForm._parse_field(question)
            for question in self.question_set.questions.all()
        }
        values = {
            key: (
                QuestionSetForm._parse_list(value)
                if isinstance(fields[key], forms.MultipleChoiceField) and not isinstance(value, list)
                else value
            )
            for key, value in values.items()
            if key in fields
        }
        super().__init__(values, *args, **kwargs)
        for key, field in fields.items():
            self.fields[key] = field

    @staticmethod
    def _parse_field(question):
        choices = [
            (answer.slug, answer.text)
            for answer in question.answers.all()
        ]
        label = question.text
        return (
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
    
    @staticmethod
    def _parse_list(value):
        return [
            v.strip()
            for v in value.split(",")
        ]

    @staticmethod
    def _clean_value(question, value):
        return (
            list(question.answers.filter(slug__in=value).all())
            if isinstance(value, list)
            else question.answers.get(slug=value)
        )

    def clean(self):
        cleaned_data = super().clean()
        questions = list(self.question_set.questions.all())
        responses = {
            question.slug: QuestionSetForm._clean_value(question, cleaned_data[question.slug])
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
