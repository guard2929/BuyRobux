from decimal import InvalidOperation

from django.contrib import admin
from .models import CustomUser, Purchase, Withdrawal
from django.db.models import F

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('roblox_nick', 'roblox_user_id', 'promo_code', 'bonus_balance', 'is_active')

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'robux_amount', 'get_price_display', 'gamepass_id', 'place_name', 'promo_code_used', 'created_at')

    def get_price_display(self, obj):
        try:
            return float(obj.price) if obj.price is not None else '0.00'
        except (ValueError, TypeError, InvalidOperation):
            return 'Invalid Price'
    get_price_display.short_description = 'Price'

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'gamepass_id', 'status', 'created_at')