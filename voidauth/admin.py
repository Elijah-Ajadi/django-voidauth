from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import VoidAuthProfile

class VoidAuthProfileInline(admin.StackedInline):
    model = VoidAuthProfile
    can_delete = False
    verbose_name_plural = 'VoidAuth Profiles'
    readonly_fields = ('public_key', 'is_void_secured', 'vetting_period_end')
    exclude = ('recovery_blob',)  # Never show the recovery blob in admin

class UserAdmin(BaseUserAdmin):
    inlines = (VoidAuthProfileInline,)
    
    # Optional: Add a column to list_display to show Void-Secured status
    list_display = BaseUserAdmin.list_display + ('is_void_secured',)
    
    def is_void_secured(self, obj):
        try:
            return obj.voidauth_profile.is_void_secured
        except VoidAuthProfile.DoesNotExist:
            return False
    is_void_secured.boolean = True
    is_void_secured.short_description = 'Void-Secured'

# No forced re-registration here to avoid conflicts with custom User models.
# Developers can import VoidAuthProfileInline and add it to their UserAdmin.
