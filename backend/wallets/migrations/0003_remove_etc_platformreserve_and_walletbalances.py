from django.db import migrations


def delete_etc_reserve_and_wallets(apps, schema_editor):
    Asset = apps.get_model('rates', 'Asset')
    PlatformReserve = apps.get_model('wallets', 'PlatformReserve')
    WalletBalance = apps.get_model('wallets', 'WalletBalance')

    try:
        etc_asset = Asset.objects.get(code='ETC')
    except Asset.DoesNotExist:
        return

    nonzero = WalletBalance.objects.filter(asset=etc_asset).exclude(balance=0).exclude(locked_balance=0).exists()
    if nonzero:
        raise RuntimeError('Cannot remove ETC assets: some WalletBalance records have non-zero balances')

    WalletBalance.objects.filter(asset=etc_asset).delete()
    PlatformReserve.objects.filter(asset=etc_asset).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0002_platformaccount_deposittransaction_platformreserve_and_more'),
        ('rates', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_etc_reserve_and_wallets, reverse_code=migrations.RunPython.noop),
    ]
