from decimal import Decimal
from .models import CurrencyRate


class CurrencyRatesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Добавляем курсы валют в объект запроса
        request.rub_rate = self.get_rate('RUB', default=Decimal('0.10'))
        request.usd_rate = self.get_rate('USD', default=Decimal('0.016'))

        response = self.get_response(request)
        return response

    def get_rate(self, currency, default):
        try:
            return CurrencyRate.objects.get(currency=currency).rate
        except CurrencyRate.DoesNotExist:
            return default