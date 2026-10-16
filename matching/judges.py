from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import F
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from .models import JudgeInvite
from .registration import token_digest

@csrf_protect
def judges(request):
    token = (request.GET.get('invite', '') if request.method == 'GET' else request.POST.get('invite', '')).strip()
    valid = len(token) >= 32 and JudgeInvite.objects.filter(token_hash=token_digest(token), active=True,
        expires_at__gt=timezone.now(), signups__lt=F('max_signups')).exists()
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if not valid:
            form.add_error(None, 'Invitation expired, disabled or full.')
        elif form.is_valid():
            with transaction.atomic():
                updated = JudgeInvite.objects.filter(token_hash=token_digest(token), active=True,
                    expires_at__gt=timezone.now(), signups__lt=F('max_signups')).update(signups=F('signups') + 1)
                if not updated:
                    form.add_error(None, 'All judge places are taken. Contact the project creator.')
                else:
                    user = form.save()
                    login(request, user)
                    return redirect('/')
    response = render(request, 'judges.html', {'form': form, 'invite': token, 'valid_invite': valid})
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response
