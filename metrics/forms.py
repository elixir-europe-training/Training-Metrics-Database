from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm
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


class EventForm(forms.ModelForm):
    class Meta:
        model = models.Event
        fields = ("code", 'organising_institution',
                  'node', 'url')
