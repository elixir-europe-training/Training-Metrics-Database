from django.conf import settings
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from metrics.models import (
    Event,
    Question,
    QuestionSet,
    QuestionSuperSet,
    Answer,
    Response,
    ResponseSet
)


@admin.register(Event)
class EventAdmin(ModelAdmin):
    pass


class ResponseAdmin(admin.TabularInline):
    model = Response


@admin.register(ResponseSet)
class ResponseSetAdmin(ModelAdmin):
    inlines = [
        ResponseAdmin,
    ]


@admin.register(QuestionSet)
class QuestionSetAdmin(ModelAdmin):
    pass


@admin.register(QuestionSuperSet)
class QuestionSuperSetAdmin(ModelAdmin):
    pass


class AnswerAdmin(admin.TabularInline):
    model = Answer

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ["text"]}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["text"]}
    list_display = (
        "text",
    )
    inlines = [
        AnswerAdmin,
    ]
