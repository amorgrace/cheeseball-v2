

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authenticator', '0006_customuser_referred_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='referral_reward_paid',
            field=models.BooleanField(default=False),
        ),
    ]
