import hashlib
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import F
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from .models import Invitation, JudgeInvite

def token_digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

@csrf_protect
def register(request):
    token = (request.GET.get('invite', '') if request.method == 'GET' else request.POST.get('invite', '')).strip()
    digest = token_digest(token)
    now = timezone.now()
    single_use = len(token) >= 32 and Invitation.objects.filter(
        token_hash=digest, used_at__isnull=True, expires_at__gt=now
    ).exists()
    shared = len(token) >= 32 and JudgeInvite.objects.filter(
        token_hash=digest, active=True, expires_at__gt=now, signups__lt=F('max_signups')
    ).exists()
    valid = single_use or shared
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if not valid:
            form.add_error(None, 'This invitation is invalid, expired or has reached its registration limit.')
        elif form.is_valid():
            with transaction.atomic():
                if single_use:
                    claimed = Invitation.objects.filter(
                        token_hash=digest, used_at__isnull=True, expires_at__gt=timezone.now()
                    ).update(used_at=timezone.now())
                else:
                    claimed = JudgeInvite.objects.filter(
                        token_hash=digest, active=True, expires_at__gt=timezone.now(),
                        signups__lt=F('max_signups')
                    ).update(signups=F('signups') + 1)
                if not claimed:
                    form.add_error(None, 'This invitation is no longer available.')
                else:
                    user = form.save()
                    if single_use:
                        Invitation.objects.filter(token_hash=digest).update(used_by=user)
                    login(request, user)
                    return redirect('/')
    response = render(request, 'register.html', {'form': form, 'invite': token, 'valid_invite': valid})
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response
