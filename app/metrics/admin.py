from django import utils
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Q

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


COMMON_EXCLUDES = [
    "user",
    "node"
]


def is_owner_of_object(user, obj):
    return (
        not obj
        or user.is_superuser
        or UserProfile.get_node(user) == obj.node
    )


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    pass


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
        "slug",
        "node",
        "user",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        user_node = UserProfile.get_node(request.user)
        query = Q(node__isnull=True)
        if user_node:
            query = query | Q(node=user_node)

        return qs.filter(query)

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = UserProfile.get_node(request.user)
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
            user_node = UserProfile.get_node(request.user)
            if not request.user.is_superuser and user_node:
                # Filter questions to only those that belong to the user's node
                kwargs["queryset"] = Question.objects.filter(node=user_node)
            elif not request.user.is_superuser:
                # If node user has no associated node, they see no questions
                kwargs["queryset"] = Question.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        return (
            readonly_fields
            if request.user.is_superuser
            else
            [*readonly_fields, "slug"]
        )

    def get_prepopulated_fields(self, request, obj=None):
        prepopulated_fields = super().get_prepopulated_fields(request, obj)

        return (
            prepopulated_fields
            if request.user.is_superuser
            else
            {}
        )


@admin.register(QuestionSuperSet)
class QuestionSuperSetAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ["name"]}

    list_display = (
        "name",
        "slug",
        "node",
        "user",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        user_node = UserProfile.get_node(request.user)
        query = Q(node__isnull=True) | Q(user=request.user)
        if user_node:
            query = query | Q(node=user_node)

        return qs.filter(query)

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = UserProfile.get_node(request.user)
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

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        return (
            readonly_fields
            if request.user.is_superuser
            else
            [*readonly_fields, "slug"]
        )

    def get_prepopulated_fields(self, request, obj=None):
        prepopulated_fields = super().get_prepopulated_fields(request, obj)

        return (
            prepopulated_fields
            if request.user.is_superuser
            else
            {}
        )


class AnswerAdmin(admin.TabularInline):
    model = Answer

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        user_node = UserProfile.get_node(request.user)
        query = Q(question__node__isnull=True) | Q(user=request.user)
        if user_node:
            query = query | Q(question__node=user_node)

        return qs.filter(query)

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
        "slug",
        "node",
        "user",
    )
    inlines = [
        AnswerAdmin,
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        user_node = UserProfile.get_node(request.user)
        query = Q(node__isnull=True) | Q(user=request.user)
        if user_node:
            query = query | Q(node=user_node)

        return qs.filter(query)

    def save_model(self, request, obj, form, change):
        if 'user' in form.cleaned_data:
            obj.user = form.cleaned_data['user']
        else:
            obj.user = request.user
        if not request.user.is_superuser:
            obj.node = UserProfile.get_node(request.user)
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

    def has_change_permission(self, request, obj=None):
        # Can only change sets from own node
        return (
            is_owner_of_object(request.user, obj)
            and super().has_change_permission(request, obj=obj)
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        return (
            readonly_fields
            if request.user.is_superuser
            else
            [*readonly_fields, "slug"]
        )

    def get_prepopulated_fields(self, request, obj=None):
        prepopulated_fields = super().get_prepopulated_fields(request, obj)

        return (
            prepopulated_fields
            if request.user.is_superuser
            else
            {}
        )


class CustomUserAdmin(UserAdmin):
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('password_reset_link',)
        return ()

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser and obj and obj.pk:
            return super().get_fieldsets(request, obj) + (
                ('Account Management', {'fields': ('password_reset_link',)}),
            )
        return super().get_fieldsets(request, obj)

    def get_reset_url(self, obj):
        if obj and obj.pk:
            base64_encoded_id = utils.http.urlsafe_base64_encode(utils.encoding.force_bytes(obj.id))
            token = PasswordResetTokenGenerator().make_token(obj)
            reset_url_args = {'uidb64': base64_encoded_id, 'token': token}
            reset_path = reverse('password_reset_confirm', kwargs=reset_url_args)
            return reset_path

    def password_reset_link(self, obj):
        if obj and obj.pk:
            url = self.get_reset_url(obj)
            return format_html('<a href="{url}">Reset Password</a>', url=url)

    password_reset_link.short_description = "Password Reset Link"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
