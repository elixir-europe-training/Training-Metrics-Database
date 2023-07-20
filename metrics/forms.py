from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from metrics.models import User


class UserLoginForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', 'Log in', css_class='btn btn-dark'))

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ["username"]
