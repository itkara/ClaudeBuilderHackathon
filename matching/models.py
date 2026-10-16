from django.conf import settings
from django.db import models

class DailyAIUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day = models.DateField()
    requests = models.PositiveIntegerField(default=0)
    generations = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'day'], name='unique_daily_ai_usage')]

class UserWorkspace(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hireationship_workspace')
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

class Invitation(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
