import hashlib
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect


def token_digest(value):
    # Kept for existing invitation-management tools and stored invite records.
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


@csrf_protect
def register(request):
    if request.user.is_authenticated:
        return redirect('/')
    form = UserCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('/')
    response = render(request, 'register.html', {'form': form})
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response
