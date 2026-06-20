from django.contrib import admin

from .models import Conversion, Ledger, RateLock, WalletBalance, Withdrawal


@admin.register(WalletBalance)
class WalletBalanceAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "balance", "locked_balance", "updated_at")
    list_filter = ("asset",)
    search_fields = ("user__email", "asset__code")


@admin.register(RateLock)
class RateLockAdmin(admin.ModelAdmin):
    list_display = ("user", "from_asset", "to_asset", "from_amount", "to_amount", "expires_at")
    list_filter = ("from_asset", "to_asset")
    search_fields = ("user__email",)


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ("user", "from_asset", "to_asset", "from_amount", "to_amount", "status", "created_at")
    list_filter = ("status", "from_asset", "to_asset")
    search_fields = ("user__email",)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "amount", "status", "created_at")
    list_filter = ("status", "asset")
    search_fields = ("user__email", "bank_account_number", "wallet_address")


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet_balance", "transaction_type", "amount", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("user__email", "reference_model")

