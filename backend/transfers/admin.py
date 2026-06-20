from django.contrib import admin
from .models import CryptoTransfer

@admin.register(CryptoTransfer)
class CryptoTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "asset", "amount", "transfer_type", "status", "created_at")
    list_filter = ("transfer_type", "status", "asset")
    search_fields = ("sender__email", "recipient__email", "recipient_address")
    readonly_fields = ("id", "created_at", "updated_at")
