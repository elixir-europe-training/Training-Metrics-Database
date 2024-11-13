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
    ResponseSet,
    UserProfile
)


EDIT_TRACKING_FIELDS = [
    "user"
]

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    pass


@admin.register(Event)
class EventAdmin(ModelAdmin):
    exclude = EDIT_TRACKING_FIELDS

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


class ResponseAdmin(admin.TabularInline):
    model = Response


@admin.register(ResponseSet)
class ResponseSetAdmin(ModelAdmin):
    exclude = EDIT_TRACKING_FIELDS
    inlines = [
        ResponseAdmin,
    ]
    list_display = (
        "event",
        "user",
    )

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


@admin.register(QuestionSet)
class QuestionSetAdmin(ModelAdmin):
    exclude = EDIT_TRACKING_FIELDS
    prepopulated_fields = {"slug": ["name"]}

    list_display = (
        "name",
        "user",
    )

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


@admin.register(QuestionSuperSet)
class QuestionSuperSetAdmin(ModelAdmin):
    exclude = EDIT_TRACKING_FIELDS
    prepopulated_fields = {"slug": ["name"]}

    list_display = (
        "name",
        "node",
        "user",
    )

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


class AnswerAdmin(admin.TabularInline):
    model = Answer
    exclude = EDIT_TRACKING_FIELDS

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ["text"]}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["text"]}
    exclude = EDIT_TRACKING_FIELDS
    list_display = (
        "text",
        "user",
    )
    inlines = [
        AnswerAdmin,
    ]

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        for instance in formset.save(commit=False):
            instance.user = request.user
        return super().save_formset(request, form, formset, change)