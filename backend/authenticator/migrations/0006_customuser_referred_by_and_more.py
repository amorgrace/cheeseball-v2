

import secrets
import string

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


REFERRAL_CODE_LENGTH = 6
REFERRAL_CODE_PREFIX = "CB"


def populate_referral_codes(apps, schema_editor):
    CustomUser = apps.get_model("authenticator", "CustomUser")
    alphabet = string.ascii_uppercase + string.digits
    existing_codes = set()

    for user in CustomUser.objects.all():

        if (
            user.referral_code
            and user.referral_code.startswith(REFERRAL_CODE_PREFIX)
            and len(user.referral_code) == len(REFERRAL_CODE_PREFIX) + REFERRAL_CODE_LENGTH
            and user.referral_code not in existing_codes
        ):
            existing_codes.add(user.referral_code)
            continue


        while True:
            suffix = "".join(secrets.choice(alphabet) for _ in range(REFERRAL_CODE_LENGTH))
            code = f"{REFERRAL_CODE_PREFIX}{suffix}"
            if code not in existing_codes:
                existing_codes.add(code)
                user.referral_code = code
                user.save(update_fields=["referral_code"])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('authenticator', '0005_remove_customuser_reset_password_token_and_more'),
    ]

    operations = [

        migrations.AddField(
            model_name='customuser',
            name='referred_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to=settings.AUTH_USER_MODEL),
        ),

        migrations.AlterField(
            model_name='customuser',
            name='referral_code',
            field=models.CharField(blank=True, default="", max_length=10),
        ),

        migrations.RunPython(populate_referral_codes, migrations.RunPython.noop),

        migrations.AlterField(
            model_name='customuser',
            name='referral_code',
            field=models.CharField(blank=True, max_length=10, unique=True),
        ),
    ]
