from django.contrib import admin

from .models import TatumAddressSubscription, TatumWebhookEvent


@admin.register(TatumAddressSubscription)
class TatumAddressSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("address", "chain", "tatum_subscription_id", "status", "created_at")
    list_filter = ("chain", "status")
    search_fields = ("address", "tatum_subscription_id", "hd_address__user__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(TatumWebhookEvent)
class TatumWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("tatum_event_id", "event_type", "address", "chain", "processed_at", "created_at")
    list_filter = ("event_type", "chain")
    search_fields = ("tatum_event_id", "address", "event_type")
    readonly_fields = ("id", "created_at", "processed_at")
