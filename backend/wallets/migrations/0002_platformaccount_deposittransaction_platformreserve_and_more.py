import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0004_asset_alter_rateconfiguration_options_and_more'),
        ('wallets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform_address', models.CharField(max_length=255)),
                ('network', models.CharField(blank=True, max_length=50)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.OneToOneField(db_column='asset', on_delete=django.db.models.deletion.PROTECT, related_name='platform_account', to='rates.asset', to_field='code')),
            ],
            options={
                'db_table': 'broker_platformaccount',
                'ordering': ['asset__code'],
            },
        ),
        migrations.CreateModel(
            name='DepositTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('expected_amount', models.DecimalField(decimal_places=8, max_digits=30)),
                ('actual_amount', models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True)),
                ('reference_code', models.CharField(max_length=64, unique=True)),
                ('external_reference', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deposits', to=settings.AUTH_USER_MODEL)),
                ('platform_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='deposits', to='wallets.platformaccount')),
            ],
            options={
                'db_table': 'broker_deposittransaction',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlatformReserve',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=8, default=0, max_digits=30)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.OneToOneField(db_column='asset', on_delete=django.db.models.deletion.PROTECT, related_name='platform_reserve', to='rates.asset', to_field='code')),
            ],
            options={
                'db_table': 'broker_platformreserve',
                'ordering': ['asset__code'],
            },
        ),
        migrations.CreateModel(
            name='ReserveMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('in', 'In'), ('out', 'Out')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=30)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('asset', models.ForeignKey(db_column='asset', on_delete=django.db.models.deletion.PROTECT, related_name='reserve_movements', to='rates.asset', to_field='code')),
            ],
            options={
                'db_table': 'broker_reservemovement',
                'ordering': ['-created_at'],
            },
        ),
    ]
