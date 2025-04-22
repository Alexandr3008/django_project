from rest_framework import serializers
from .models import Parcel, ParcelType

class ParcelTypeSerializer(serializers.ModelSerializer):
    """Сериализатор для типов посылок."""
    class Meta:
        model = ParcelType
        fields = ['id', 'name']

class ParcelSerializer(serializers.ModelSerializer):
    """Сериализатор для посылок с валидацией."""
    type = serializers.PrimaryKeyRelatedField(queryset=ParcelType.objects.all())  # ID типа
    type_name = serializers.CharField(source='type.name', read_only=True)  # Имя типа

    class Meta:
        model = Parcel
        fields = ['id', 'session_key', 'name', 'weight', 'type', 'type_name', 'value', 'delivery_cost', 'created_at']
        read_only_fields = ['id', 'delivery_cost', 'created_at']

    def validate_weight(self, value):
        """Проверка, что вес положительный."""
        if value <= 0:
            raise serializers.ValidationError("Вес должен быть положительным")
        return value

    def validate_value(self, value):
        """Проверка, что стоимость неотрицательная."""
        if value < 0:
            raise serializers.ValidationError("Стоимость не может быть отрицательной")
        return value