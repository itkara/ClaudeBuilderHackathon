from django.contrib import admin
from .models import JudgeInvite

@admin.register(JudgeInvite)
class JudgeInviteAdmin(admin.ModelAdmin):
    list_display = ('label', 'signups', 'max_signups', 'expires_at', 'active')
    list_editable = ('max_signups', 'active')
    readonly_fields = ('token_hash', 'signups', 'created_at')
    fields = ('label', 'signups', 'max_signups', 'expires_at', 'active', 'token_hash', 'created_at')
    def has_add_permission(self, request):
        return False
