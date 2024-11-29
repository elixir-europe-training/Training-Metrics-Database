from django.conf import settings
from django import utils
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from metrics.models import Event
from django.utils.html import format_html


@admin.register(Event)
class EventAdmin(ModelAdmin):
    pass


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