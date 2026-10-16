import hashlib
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from .models import Invitation

def token_digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

@csrf_protect
def register(request):
    token = request.GET.get('invite', '') if request.method == 'GET' else request.POST.get('invite', '')
    token = token.strip()
    valid = len(token) >= 32 and Invitation.objects.filter(
        token_hash=token_digest(token), used_at__isnull=True, expires_at__gt=timezone.now()
    ).exists()
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if not valid:
            form.add_error(None, 'This invitation is invalid, expired or already used.')
        elif form.is_valid():
            with transaction.atomic():
                claimed = Invitation.objects.filter(
                    token_hash=token_digest(token), used_at__isnull=True, expires_at__gt=timezone.now()
                ).update(used_at=timezone.now())
                if not claimed:
                    form.add_error(None, 'This invitation has already been used.')
                else:
                    user = form.save()
                    Invitation.objects.filter(token_hash=token_digest(token)).update(used_by=user)
                    login(request, user)
                    return redirect('/')
    return render(request, 'register.html', {'form': form, 'invite': token, 'valid_invite': valid})
