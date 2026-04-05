from django.contrib import admin

from .models import PaymentRecord


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "method", "status", "provider_reference", "created_at")
    list_filter = ("method", "status", "provider")
    search_fields = ("transaction__id", "provider_reference", "receipt_reference")
    readonly_fields = ("created_at", "updated_at", "user_confirmed_at", "verified_at")
