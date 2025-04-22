from django.db import models

class ParcelType(models.Model):
    """Типы посылок: одежда, электроника, разное."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Parcel(models.Model):
    """Модель посылки с данными пользователя."""
    session_key = models.CharField(max_length=40, db_index=True)  # Для отслеживания сессии
    name = models.CharField(max_length=100)  # Название посылки
    weight = models.FloatField(help_text="Вес в кг")  # Вес в кг
    type = models.ForeignKey(ParcelType, on_delete=models.PROTECT)  # Тип посылки
    value = models.FloatField(help_text="Стоимость в USD")  # Стоимость в долларах
    delivery_cost = models.FloatField(null=True, blank=True, help_text="Стоимость доставки в RUB")  # Стоимость доставки
    created_at = models.DateTimeField(auto_now_add=True)  # Дата создания

    def __str__(self):
        return self.name


