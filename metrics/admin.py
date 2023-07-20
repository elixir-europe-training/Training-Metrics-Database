from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from metrics.models import User


# Register your models here.
@admin.register(User)
class UserAdmin(ModelAdmin):
    pass
