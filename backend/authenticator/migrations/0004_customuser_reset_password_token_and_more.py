

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authenticator', '0003_customuser_verification_token_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='reset_password_token',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='reset_password_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
