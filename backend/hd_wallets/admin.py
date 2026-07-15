from django.contrib import admin

from .models import HdWalletAddress, HdWalletDerivationIndex, OnChainDeposit, OnChainWithdrawal


@admin.register(HdWalletDerivationIndex)
class HdWalletDerivationIndexAdmin(admin.ModelAdmin):
    list_display = ("user", "chain", "network", "derivation_index", "created_at")
    list_filter = ("chain", "network")
    search_fields = ("user__email", "chain", "network")
    readonly_fields = ("id", "created_at")


@admin.register(HdWalletAddress)
class HdWalletAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "network", "chain", "address", "status", "created_at")
    list_filter = ("chain", "network", "status", "currency")
    search_fields = ("user__email", "address", "currency")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OnChainDeposit)
class OnChainDepositAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "network", "status", "txid", "created_at")
    list_filter = ("status", "currency", "network")
    search_fields = ("user__email", "txid", "currency")
    readonly_fields = ("id", "created_at", "updated_at", "credited_at")


@admin.register(OnChainWithdrawal)
class OnChainWithdrawalAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "network", "to_address", "status", "created_at")
    list_filter = ("status", "currency", "network")
    search_fields = ("user__email", "txid", "to_address")
    readonly_fields = ("id", "created_at", "updated_at")
