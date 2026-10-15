from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect

class PrivateAppMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/static/') or path in ('/login/', '/favicon.ico'):
            return self.get_response(request)
        if not request.user.is_authenticated:
            if path.startswith('/api/'):
                return JsonResponse({'error': 'Login required.'}, status=401)
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
