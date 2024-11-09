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


EDIT_TRACKING_FIELDS = [
    "user"
]


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
    prepopulated_fields = {"slug": ["name"]}

    list_display = (
        "name",
        "user",
    )

    def get_queryset(self, request):
        if request.user.is_superuser:
            qs = super().get_queryset(request)
            return qs
        qs = super().get_queryset(request)
        # Filter QuestionSets based on the node of associated QuestionSuperSets
        exclude = EDIT_TRACKING_FIELDS  # needs to be included if we want to be able to change user for a set
        return qs.filter(
                user = request.user
        ).distinct() | qs.filter(user__is_superuser = True).distinct()

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        return super().save_model(request, obj, form, change)
    
    def has_change_permission(self, request, obj = None):
        # Node users can only change their own objects, not those of the superuser
        if obj and obj.user != request.user and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj = None):
        # Node users cannot delete superuser objects
        if obj and obj.user != request.user and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_fields(self, request, obj = None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in EDIT_TRACKING_FIELDS]
        return fields


@admin.register(QuestionSuperSet)
class QuestionSuperSetAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ["name"]}

    list_display = (
        "name",
        "node",
        "user",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter QuestionSuperSets based on the user's node or allow them to view shared supersets
        return qs.filter(
                user = request.user
        ).distinct() | qs.filter(user__is_superuser = True).distinct()

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        return super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj = None):
        # Node users can only change their own objects, not those of the superuser
        if obj and obj.user != request.user and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj = None):
        # Node users cannot delete superuser objects
        if obj and obj.user != request.user and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_fields(self, request, obj = None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in EDIT_TRACKING_FIELDS]
        return fields


class AnswerAdmin(admin.TabularInline):
    model = Answer

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter QuestionSuperSets based on the user's node or allow them to view shared supersets (node=None)
        return qs.filter(
            user = request.user
        ).distinct()

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ["text"]}

    def get_fields(self, request, obj = None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in EDIT_TRACKING_FIELDS]
        return fields


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ["text"]}
    list_display = (
        "text",
        "user",
    )
    inlines = [
        AnswerAdmin,
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter Questions through QuestionSets linked to QuestionSuperSets that match the user's node
        return qs.filter(
            user = request.user
        ).distinct()

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        return super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        for instance in formset.save(commit=False):
            instance.user = request.user
        return super().save_formset(request, form, formset, change)

    def get_fields(self, request, obj = None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in EDIT_TRACKING_FIELDS]
        return fields
