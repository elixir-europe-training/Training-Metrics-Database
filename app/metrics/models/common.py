from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.urls import reverse
from django import forms
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import re
import requests
from django.contrib.auth.models import User
from django.db.models.signals import post_save


def string_choices(choices):
    return [
        (choice, choice)
        for choice in choices
    ]


class ChoiceArrayField(ArrayField):
    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.MultipleChoiceField,
            "choices": self.base_field.choices,
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)


class EditTracking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Event(EditTracking):
    code = models.CharField(max_length=128, unique=True, null=True, blank=True)
    title = models.CharField(max_length=1024)
    node = models.ManyToManyField("Node")
    node_main = models.ForeignKey(
        "Node", on_delete=models.CASCADE, related_name='node_main')
    date_start = models.DateField()
    date_end = models.DateField()
    duration = models.DecimalField(verbose_name="Duration (days)", max_digits=6, decimal_places=2)
    type = models.TextField(
        choices=string_choices([
            "Training - face to face",
            "Training - e-learning",
            "Training - blended",
            "Knowledge Exchange Workshop",
            "Hackathon",
        ])
    )
    organising_institution = models.ManyToManyField("OrganisingInstitution")
    location_city = models.CharField(max_length=128)
    location_country = models.CharField(max_length=128)
    funding = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "ELIXIR Converge",
            "EOSC Life",
            "EXCELERATE",
            "ELIXIR Implementation Study",
            "ELIXIR Community / Use case",
            "ELIXIR Node",
            "ELIXIR Hub",
            "ELIXIR Platform",
            "Non-ELIXIR / Non-EXCELERATE Funds",
        ])
    ))


    target_audience = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Academia/ Research Institution",
            "Industry",
            "Non-Profit Organisation",
            "Healthcare",
        ])
    ))

    additional_platforms = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Compute",
            "Data",
            "Interoperability",
            "Tools",
            "NA",
        ])
    ))

    communities = ChoiceArrayField(base_field=models.TextField(
        choices=string_choices([
            "Human Data",
            "Marine Metagenomics",
            "Rare Diseases",
            "Plant Sciences",
            "Proteomics",
            "Metabolomics",
            "Galaxy",
            "NA",
        ])
    ))

    number_participants = models.PositiveIntegerField()
    number_trainers = models.PositiveIntegerField()
    url = models.URLField(max_length=4096)
    status = models.TextField(
        choices=string_choices([
            "Complete",
            "Incomplete",
        ])
    )
    locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.id}) ({self.code})"
    

    def get_absolute_url(self):
        return reverse("event-edit", kwargs={"pk": self.id})
    

    @property
    def location(self):
        return (
            self.location_city,
            self.location_country
        )
    
    @property
    def date_period(self):
        return (
            self.date_start,
            self.date_end
        )
    
    @property
    def is_locked(self):
        return (
            self.code is not None
            or self.locked
        )


class Node(models.Model):
    name = models.TextField()
    country = models.TextField()

    def __str__(self):
        return (
            f"{self.name} ({self.country})"
            if self.country
            else self.name
        )


def is_ror_id(value):
    if re.match("^https://ror.org/[a-zA-Z0-9]+$", value):
        return value
    raise ValidationError(f"Not a valid ror id: {value}")


class OrganisingInstitution(models.Model):
    name = models.TextField()
    country = models.TextField()
    ror_id = models.URLField(max_length=512, unique=True, null=True, validators=[is_ror_id])

    def __str__(self):
        return (
            f"{self.name} ({self.country})"
            if self.country
            else str(self.name)
        )

    def get_absolute_url(self):
        return reverse("institution-edit", kwargs={"pk": self.id})

    def update_ror_data(self):
        try:
            ror_id_base = re.match("^https://ror.org/(.+)$", self.ror_id)[0]
            ror_url = f"https://api.ror.org/organizations/{ror_id_base}"
            response = requests.get(ror_url, allow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                self.name = data["name"]
                self.country = data.get("country", {}).get("country_name", "")
            else:
                raise ValidationError(f"Could not fetch ROR data for: {self.ror_id}, {ror_url}, {response.status_code}")
        except TypeError:
            raise ValidationError(f"Not a valid ror id: {self.ror_id}")


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.SET_NULL,
        null=True,
        related_name="users"
    )

    def __str__(self):
        return "Profile for {0}".format(self.user)


def get_node(self):
    try:
        return self.profile.node
    except ObjectDoesNotExist:
        return None


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        node_name = f"ELIXIR-{instance.username.upper()}"
        node = Node.objects.filter(name=node_name).first()
        UserProfile.objects.create(user=instance, node=node)


User.add_to_class("get_node", get_node)
post_save.connect(create_user_profile, sender=User)