from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ModelForm
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


class EventForm(ModelForm):
    class Meta:
        model = models.Event
        fields = [
            "title",
            "date_start",
            "date_end",
            "duration",
            "type",
            "organising_institution",
            "location_city",
            "location_country",
            "funding",
            "target_audience",
            "additional_platforms",
            "communities",
            "number_participants",
            "number_trainers",
            "url",
            "status",
        ]