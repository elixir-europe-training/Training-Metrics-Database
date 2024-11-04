from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from metrics.models import Event


@admin.register(Event)
class EventAdmin(ModelAdmin):
    pass