from django.core.management.base import BaseCommand
from parcels.tasks import calculate_delivery_costs

class Command(BaseCommand):
    help = 'Ручной запуск расчета стоимости доставки'

    def handle(self, *args, **kwargs):
        calculate_delivery_costs()
        self.stdout.write(self.style.SUCCESS('Стоимость доставки рассчитана вручную'))