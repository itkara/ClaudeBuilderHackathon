import os
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from .models import DailyAIUsage
from django.http import JsonResponse
from django.shortcuts import redirect

class PrivateAppMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/static/') or path in ('/login/', '/register/', '/judges/', '/favicon.ico'):
            return self.get_response(request)
        if not request.user.is_authenticated:
            if path.startswith('/api/'):
                return JsonResponse({'error': 'Login required.'}, status=401)
            return redirect(settings.LOGIN_URL)
        if path == '/api/generate' and request.method == 'POST':
            limit = max(0, int(os.getenv('HIREATIONSHIP_DAILY_GENERATION_LIMIT', '3')))
            usage, _ = DailyAIUsage.objects.get_or_create(user=request.user, day=timezone.localdate())
            updated = DailyAIUsage.objects.filter(pk=usage.pk, generations__lt=limit).update(generations=F('generations') + 1)
            if not updated:
                return JsonResponse({'error': f'Daily application generation limit reached ({limit}). Try again tomorrow.'}, status=429)
        if path in ('/api/profile', '/api/match', '/api/jd', '/api/generate') and request.method == 'POST' and os.getenv('ANTHROPIC_API_KEY'):
            if os.getenv('HIREATIONSHIP_AI_ENABLED', '1') == '0':
                return JsonResponse({'error': 'AI features are temporarily disabled.'}, status=503)
            limit = max(0, int(os.getenv('HIREATIONSHIP_DAILY_AI_LIMIT', '20')))
            usage, _ = DailyAIUsage.objects.get_or_create(user=request.user, day=timezone.localdate())
            updated = DailyAIUsage.objects.filter(pk=usage.pk, requests__lt=limit).update(requests=F('requests') + 1)
            if not updated:
                return JsonResponse({'error': 'Daily AI request limit reached. Try again tomorrow.'}, status=429)
        return self.get_response(request)
