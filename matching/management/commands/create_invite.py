import secrets
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from matching.models import Invitation
from matching.registration import token_digest

class Command(BaseCommand):
    help = 'Create a single-use registration invitation (default expiry: 7 days).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)

    def handle(self, *args, **options):
        days = options['days']
        if not 1 <= days <= 30:
            raise ValueError('Choose an expiry between 1 and 30 days.')
        token = secrets.token_urlsafe(32)
        Invitation.objects.create(token_hash=token_digest(token), expires_at=timezone.now() + timedelta(days=days))
        self.stdout.write(f'Invitation link (share privately; shown only once): https://itkara.pythonanywhere.com/register/?invite={token}')
