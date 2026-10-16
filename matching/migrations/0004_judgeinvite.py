from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta

def seed(apps, schema_editor):
    apps.get_model('matching', 'JudgeInvite').objects.create(
        token_hash='cf96888b93e823c0749c708391b58da4d9fc122efeafc47186d237fcc281facb',
        label='Hackathon judges', max_signups=15,
        expires_at=timezone.now() + timedelta(days=30))

class Migration(migrations.Migration):
    dependencies = [('matching', '0003_invitation')]
    operations = [
        migrations.CreateModel(name='JudgeInvite', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('token_hash', models.CharField(max_length=64, unique=True)),
            ('label', models.CharField(default='Hackathon judges', max_length=100)),
            ('max_signups', models.PositiveIntegerField(default=15)),
            ('signups', models.PositiveIntegerField(default=0)),
            ('expires_at', models.DateTimeField()),
            ('active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
