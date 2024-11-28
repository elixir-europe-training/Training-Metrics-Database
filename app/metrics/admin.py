from django.contrib import admin
from django.contrib.admin import ModelAdmin
from metrics.token import create_signup_token
from django.urls import reverse


from metrics.models import (
    Event,
    Question,
    QuestionSet,
    QuestionSuperSet,
    Answer,
    Response,
    ResponseSet,
    UserProfile,
    Node
)
from django.utils.safestring import mark_safe


COMMON_EXCLUDES = [
    "user",
    "node"
]


def is_owner_of_object(user, obj):
    return (
        not obj
        or user.is_superuser
        or user.get_node() == obj.node
    )


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    def signup_link(self, obj):
        token = create_signup_token(obj.user)
        token_url = f"{reverse('jwt-signup')}?token={token}"
        return mark_safe(f'<a href="{token_url}" target="_blank">Sign up link</a>')

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser and obj and obj.allow_token_reset:
            return ("signup_link",)
        return ()

    signup_link.short_description = "Sign up link"


@admin.register(Node)
class NodeAdmin(ModelAdmin):
    pass


@admin.register(Event)
class EventAdmin(ModelAdmin):
    exclude = COMMON_EXCLUDES

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        return super().save_model(request, obj, form, change)


class ResponseAdmin(admin.TabularInline):
    model = Response


@admin.register(ResponseSet)
class ResponseSetAdmin(ModelAdmin):
    exclude = COMMON_EXCLUDES
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
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        user_node = request.user.get_node()
        if user_node:
            # Filter QuestionSets based on the node
            return qs.filter(
                    node=user_node
            ).distinct() | qs.filter(node=None).distinct()
        return qs.none()

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = request.user.get_node()
        return super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        # Can only change sets from own node
        return (
            is_owner_of_object(request.user, obj)
            and super().has_change_permission(request, obj=obj)
        )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in COMMON_EXCLUDES]
        return fields

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "questions":
            user_node = request.user.get_node()
            if not request.user.is_superuser and user_node:
                # Filter questions to only those that belong to the user's node
                kwargs["queryset"] = Question.objects.filter(node=user_node)
            elif not request.user.is_superuser:
                # If node user has no associated node, they see no questions
                kwargs["queryset"] = Question.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)


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

        user_node = request.user.get_node()
        if user_node:
            # Filter QuestionSuperSets based on the node
            return qs.filter(
                    node=user_node
            ).distinct() | qs.filter(node=None).distinct()

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = request.user.get_node()
        return super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return (
            is_owner_of_object(request.user, obj)
            and super().has_change_permission(request, obj=obj)
        )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in COMMON_EXCLUDES]
        return fields


class AnswerAdmin(admin.TabularInline):
    model = Answer

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter QuestionSuperSets based on the user's node or allow them to view shared supersets (node=None)
        return qs.filter(
            user=request.user
        ).distinct()

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ["text"]}

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in COMMON_EXCLUDES]
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

        user_node = request.user.get_node()
        if user_node:
            return qs.filter(node=user_node)
        return qs.none()  # No node

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = request.user.get_node()
        return super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        for instance in formset.save(commit=False):
            instance.user = request.user
        return super().save_formset(request, form, formset, change)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [field for field in fields if field not in COMMON_EXCLUDES]
        return fields
