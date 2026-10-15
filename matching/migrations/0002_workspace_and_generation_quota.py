from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('matching', '0001_initial')]
    operations = [
        migrations.AddField(model_name='dailyaiusage', name='generations', field=models.PositiveIntegerField(default=0)),
        migrations.CreateModel(
            name='UserWorkspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hireationship_workspace', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
