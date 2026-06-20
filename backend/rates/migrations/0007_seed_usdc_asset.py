from django.db import migrations


def seed_usdc(apps, schema_editor):
    Asset = apps.get_model("rates", "Asset")
    RateConfiguration = apps.get_model("rates", "RateConfiguration")

    asset, created = Asset.objects.update_or_create(
        code="USDC",
        defaults={
            "name": "USD Coin",
            "binance_symbol": "USDCUSDT",
            "network": "ERC20",
            "sort_order": 35,
            "is_active": True,
        },
    )

    # In migration context, pass the Asset instance (not the string code)
    # because the historical model doesn't resolve to_field="code" shortcuts.
    RateConfiguration.objects.get_or_create(
        asset=asset,
        defaults={
            "buy_markup_percent": "3.00",
            "sell_markup_percent": "2.00",
            "fallback_market_rate": "1600",
        },
    )

    if created:
        print("[OK] USDC asset seeded.")
    else:
        print("[INFO] USDC asset already existed - updated.")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rates", "0006_ratequote_crypto_usd_price"),
    ]

    operations = [
        migrations.RunPython(seed_usdc, noop_reverse),
    ]
