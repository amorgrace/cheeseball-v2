

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0003_alter_transaction_asset'),
        ('rates', '0004_asset_alter_rateconfiguration_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='asset',
            field=models.ForeignKey(db_column='asset', on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='rates.asset', to_field='code'),
        ),
    ]
