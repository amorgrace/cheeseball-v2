from django.contrib import admin

from .models import QuidaxDeposit, QuidaxSubAccount, QuidaxWalletAddress, QuidaxWebhookEvent, QuidaxWithdrawal


@admin.register(QuidaxSubAccount)
class QuidaxSubAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "quidax_id", "email", "created_at")
    search_fields = ("user__email", "quidax_id", "email")


@admin.register(QuidaxWalletAddress)
class QuidaxWalletAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "network", "status", "address", "updated_at")
    list_filter = ("currency", "network", "status")
    search_fields = ("user__email", "address")


@admin.register(QuidaxDeposit)
class QuidaxDepositAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "network", "amount", "status", "txid", "credited_at")
    list_filter = ("currency", "network", "status")
    search_fields = ("user__email", "txid", "provider_reference")


@admin.register(QuidaxWithdrawal)
class QuidaxWithdrawalAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "network", "amount", "status", "reference", "created_at")
    list_filter = ("currency", "network", "status")
    search_fields = ("user__email", "reference", "address")


@admin.register(QuidaxWebhookEvent)
class QuidaxWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "provider_event_id", "processed_at", "created_at")
    search_fields = ("event_type", "provider_event_id")
