from django.contrib import admin

from .models import Asset, RateConfiguration, RateQuote


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "binance_symbol", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "binance_symbol")
    ordering = ("sort_order", "code")


@admin.register(RateConfiguration)
class RateConfigurationAdmin(admin.ModelAdmin):
    list_display = ("asset", "buy_markup_percent", "sell_markup_percent", "fallback_market_rate")
    list_select_related = ("asset",)
    search_fields = ("asset__code", "asset__name")


@admin.register(RateQuote)
class RateQuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "asset", "quote_type", "final_rate", "source", "created_at", "expires_at")
    list_filter = ("quote_type", "source", "asset")
    list_select_related = ("asset",)
    readonly_fields = ("created_at",)
