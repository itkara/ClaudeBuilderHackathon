"""Per-request AI credentials; user keys are never stored in workspace data."""
import os
from contextvars import ContextVar
from django.http import JsonResponse

api_key = ContextVar('anthropic_api_key', default=None)


class OptionalAIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        mode = request.headers.get('X-AI-Mode', 'free')
        key = ''
        if request.user.is_authenticated and request.path.startswith('/api/'):
            if mode == 'personal':
                key = request.headers.get('X-Anthropic-Key', '').strip()
                if not key.startswith('sk-ant-') or len(key) > 512:
                    return JsonResponse({'error': 'Enter a valid Anthropic API key or select free mode.'}, status=400)
            elif mode == 'server' and os.getenv('HIREATIONSHIP_ALLOW_SHARED_CLAUDE','0') == '1':
                key = os.getenv('ANTHROPIC_API_KEY', '')
        token = api_key.set(key)
        try:
            return self.get_response(request)
        finally:
            api_key.reset(token)
