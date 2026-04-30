

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rates', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_type', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=10)),
                ('asset', models.CharField(default='BTC', max_length=10)),
                ('status', models.CharField(choices=[('pending_payment', 'Pending payment'), ('pending_review', 'Pending review'), ('paid', 'Paid'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('rejected', 'Rejected')], default='pending_payment', max_length=20)),
                ('payment_method', models.CharField(blank=True, choices=[('paystack', 'Paystack'), ('bank_transfer', 'Bank transfer')], max_length=20, null=True)),
                ('naira_amount', models.DecimalField(decimal_places=2, max_digits=20)),
                ('crypto_amount', models.DecimalField(decimal_places=8, max_digits=20)),
                ('market_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('markup_percent', models.DecimalField(decimal_places=2, max_digits=6)),
                ('final_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('wallet_address', models.CharField(blank=True, max_length=255)),
                ('network', models.CharField(blank=True, max_length=50)),
                ('broker_wallet_address', models.CharField(blank=True, max_length=255)),
                ('bank_name', models.CharField(blank=True, max_length=120)),
                ('bank_account_name', models.CharField(blank=True, max_length=120)),
                ('bank_account_number', models.CharField(blank=True, max_length=30)),
                ('admin_notes', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_broker_transactions', to=settings.AUTH_USER_MODEL)),
                ('quote', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='rates.ratequote')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
