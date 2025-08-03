import string
from decimal import InvalidOperation

from django.contrib import admin
from .models import CustomUser, Purchase, Withdrawal
from django.db.models import F
from .models import PromoCode
import random

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'promo_type', 'bonus_amount', 'is_active', 'valid_until')
    list_filter = ('promo_type', 'is_active')
    search_fields = ('code',)
    actions = ['generate_promo_codes']

    def generate_promo_codes(self, request, queryset):
        count = 10  # Количество генерируемых промокодов
        for _ in range(count):
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not PromoCode.objects.filter(code=code).exists():
                    PromoCode.objects.create(
                        code=code,
                        promo_type='general',
                        bonus_amount=10,
                        is_active=True
                    )
                    break
        self.message_user(request, f"Создано {count} промокодов")

    generate_promo_codes.short_description = "Сгенерировать общие промокоды"
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
from .models import CurrencyRate

@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'rate', 'updated_at')
    readonly_fields = ('updated_at',)