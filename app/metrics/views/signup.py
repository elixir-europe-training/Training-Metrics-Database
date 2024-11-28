import datetime
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Submit, Div
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from metrics.token import validate_token
from django.http import HttpResponseRedirect
from django.urls import reverse


class SignupForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="New password")
    password_verififaction = forms.CharField(widget=forms.PasswordInput, label="Verify password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("password"),
            Field("password_verififaction"),
            Div(
                Submit("submit", "Submit"),
                css_class="mb-3"
            ),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data["password"]
        try:
            validate_password(password)
        except ValidationError as e:
            for message in e.messages:
                self.add_error("password", message)

        if password != cleaned_data["password_verififaction"]:
            self.add_error("password_verififaction", "Passwords do not match")

        return cleaned_data


def jwt_signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form_data = form.cleaned_data
            user = validate_token(request.GET["token"])
            user.set_password(form_data["password"])
            user.profile.auth_ticker += 1
            user.save()
            user.profile.save()

            return HttpResponseRedirect(reverse("login"))

        except (ValidationError, KeyError):
            raise PermissionDenied()

    return render(
        request,
        'metrics/login.html',
        context={
            "title": "Sign up",
            "form": form,
        }
    )
    token = request.GET["token"]
