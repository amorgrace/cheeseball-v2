from django.contrib import admin

from .models import Transaction


@admin.action(description="Mark selected transactions as processing")
def mark_processing(modeladmin, request, queryset):
    queryset.update(status=Transaction.PROCESSING)


@admin.action(description="Mark selected transactions as completed")
def mark_completed(modeladmin, request, queryset):
    queryset.update(status=Transaction.COMPLETED)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "transaction_type",
        "status",
        "payment_method",
        "naira_amount",
        "crypto_amount",
        "created_at",
    )
    list_filter = ("transaction_type", "status", "payment_method", "asset")
    search_fields = ("id", "user__email", "wallet_address", "bank_account_number")
    readonly_fields = ("created_at", "updated_at", "reviewed_at", "paid_at", "completed_at", "failed_at")
    actions = [mark_processing, mark_completed]
