from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker", "0014_alter_transaction_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="expires_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    "Auto-set to 24h after creation for pending_payment transactions. "
                    "Null for pre-migration records (those are expired via created_at check)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="fail_reason",
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text="Machine-readable reason for failure, e.g. 'expired'",
            ),
        ),
    ]
