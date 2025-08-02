from celery import shared_task
from django.conf import settings
from web3 import Web3
from .models import Purchase

w3 = Web3(Web3.HTTPProvider(settings.INFURA_URL))

@shared_task
def check_pending_payments():
    pending_purchases = Purchase.objects.filter(status='pending', crypto_address__isnull=False)
    for purchase in pending_purchases:
        tx_hash, status = check_transaction_status(
            purchase.crypto_address,
            float(purchase.crypto_amount),
            settings.MIN_CONFIRMATIONS
        )
        if status == 'confirmed':
            purchase.tx_hash = tx_hash
            purchase.status = 'completed'
            purchase.save()
        elif status == 'pending':
            purchase.tx_hash = tx_hash
            purchase.save()