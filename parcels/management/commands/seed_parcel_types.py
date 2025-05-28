from django.core.management.base import BaseCommand

from parcels.models import ParcelType


class Command(BaseCommand):
    help = "Заполняет базу данных начальными типами посылок"

    def handle(self, *args, **kwargs):
        types = ["Одежда", "Электроника", "Разное"]
        for type_name in types:
            ParcelType.objects.get_or_create(name=type_name)
        self.stdout.write(self.style.SUCCESS("Типы посылок успешно добавлены"))
