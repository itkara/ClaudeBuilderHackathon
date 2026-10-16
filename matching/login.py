import os
from urllib.parse import urlencode
from django.contrib.auth.views import LoginView

class HireationshipLoginView(LoginView):
    template_name = 'login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        email = os.getenv('HIREATIONSHIP_INVITE_CONTACT_EMAIL', '').strip()
        if email and '@' in email and not any(c in email for c in '\r\n?&#'):
            query = urlencode({
                'subject': 'Hireationship — registration access request',
                'body': 'Hello,\n\nI would like to request access to Hireationship.\n\nMy name:\nUniversity or organisation (optional):\n\nI would appreciate a registration link when one is available.\n\nThank you,\n'
            })
            context['invite_request_url'] = f'mailto:{email}?{query}'
        return context
