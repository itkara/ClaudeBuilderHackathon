import secrets
from datetime import timedelta

from urllib.parse import urlencode
from django import forms
from django.contrib import admin
from django.http import HttpResponseNotAllowed
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from .models import Invitation, JudgeInvite
from .registration import token_digest


class InvitationEmailForm(forms.Form):
    recipient = forms.EmailField(label='Recipient email', max_length=254)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Create single-use registration links without storing plaintext tokens."""
    list_display = ('id', 'status', 'created_at', 'expires_at', 'used_at', 'used_by')
    list_filter = ('used_at',)
    readonly_fields = ('token_hash', 'created_at', 'expires_at', 'used_at', 'used_by')
    fields = readonly_fields
    ordering = ('-created_at',)
    change_list_template = 'admin/matching/invitation/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='Status')
    def status(self, obj):
        if obj.used_at:
            return 'Used'
        if obj.expires_at <= timezone.now():
            return 'Expired'
        return 'Available'

    def get_urls(self):
        return [
            path('generate/', self.admin_site.admin_view(self.generate_invite),
                 name='matching_invitation_generate'),
        ] + super().get_urls()

    def generate_invite(self, request):
        if not request.user.is_active or not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        url = None
        email_draft_url = None
        form = InvitationEmailForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            token = secrets.token_urlsafe(32)
            Invitation.objects.create(
                token_hash=token_digest(token),
                expires_at=timezone.now() + timedelta(days=7),
            )
            url = request.build_absolute_uri(reverse('register') + '?invite=' + token)
            recipient = form.cleaned_data['recipient']
            body = (f'Hi,\n\nThanks for your interest in Hireationship! 💘\n\n'
                    f'You can create your account using this private, single-use invitation link:\n\n'
                    f'{url}\n\nThe link expires in 7 days. Please do not share it.\n\n'
                    f'Once registered, you can upload your CV, discover job matches and draft tailored applications.\n\n'
                    f'I would really appreciate your feedback!\n\nBest wishes,\nIpek\n'
                    f'Because you should have hire standards. 💘')
            email_draft_url = 'mailto:' + recipient + '?' + urlencode({
                'subject': 'Your invitation to Hireationship 💘', 'body': body})
        elif request.method != 'GET':
            return HttpResponseNotAllowed(['GET', 'POST'])
        context = {
            **self.admin_site.each_context(request),
            'title': 'Generate a single-use invitation',
            'opts': self.model._meta,
            'registration_url': url,
            'email_draft_url': email_draft_url,
            'form': form,
        }
        response = TemplateResponse(request, 'admin/matching/invitation/generate.html', context)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


@admin.register(JudgeInvite)
class JudgeInviteAdmin(admin.ModelAdmin):
    list_display = ('label', 'signups', 'max_signups', 'expires_at', 'active')
    list_editable = ('max_signups', 'active')
    readonly_fields = ('token_hash', 'signups', 'created_at')
    fields = ('label', 'signups', 'max_signups', 'expires_at', 'active', 'token_hash', 'created_at')
    def has_add_permission(self, request):
        return False
