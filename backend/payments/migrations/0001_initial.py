

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('broker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method', models.CharField(choices=[('paystack', 'Paystack'), ('bank_transfer', 'Bank transfer')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('pending_review', 'Pending review'), ('verified', 'Verified'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('provider', models.CharField(blank=True, max_length=30)),
                ('provider_reference', models.CharField(blank=True, max_length=120)),
                ('receipt_reference', models.CharField(blank=True, max_length=255)),
                ('receipt_note', models.TextField(blank=True)),
                ('provider_payload', models.JSONField(blank=True, default=dict)),
                ('user_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_record', to='broker.transaction')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
