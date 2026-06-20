

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authenticator', '0002_customuser_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='verification_token',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='verification_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
