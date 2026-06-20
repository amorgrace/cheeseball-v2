

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authenticator", "0007_customuser_referral_reward_paid"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="kyc_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Unverified"),
                    ("submitted", "Submitted"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                default="unverified",
                max_length=20,
            ),
        ),
    ]

