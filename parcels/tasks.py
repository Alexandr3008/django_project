from celery import shared_task
from django.core.cache import cache
import requests
from .models import Parcel
import logging

logger = logging.getLogger(__name__)

@shared_task
def calculate_delivery_costs():
    """Расчет стоимости доставки для необработанных посылок."""
    exchange_rate = cache.get('usd_to_rub')
    if not exchange_rate:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
        data = response.json()
        exchange_rate = data['Valute']['USD']['Value']
        cache.set('usd_to_rub', exchange_rate, timeout=300)  # Кэш на 5 минут

    unprocessed = Parcel.objects.filter(delivery_cost__isnull=True)
    for parcel in unprocessed:
        cost = (parcel.weight * 0.5 + parcel.value * 0.01) * exchange_rate
        parcel.delivery_cost = cost
        parcel.save()
        logger.info(f"Стоимость доставки для посылки {parcel.id}: {cost} RUB")