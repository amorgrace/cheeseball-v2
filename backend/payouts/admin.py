from django.contrib import admin

from .models import BeneficiaryBankAccount


@admin.register(BeneficiaryBankAccount)
class BeneficiaryBankAccountAdmin(admin.ModelAdmin):
    list_display = ("account_name", "bank_name", "account_number", "account_type", "user", "created_at")
    list_filter = ("account_type", "bank_name")
    search_fields = ("account_name", "bank_name", "account_number", "user__email")

