import json
import logging
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase
from rest_framework.views import APIView

from parcels.exceptions import custom_exception_handler
from parcels.models import Parcel, ParcelType
from parcels.serializers import ParcelSerializer
from parcels.tasks import calculate_delivery_costs


class ParcelModelTest(TestCase):
    """Тесты для моделей Parcel и ParcelType."""

    def setUp(self):
        self.parcel_type = ParcelType.objects.create(name="Одежда")
        self.parcel = Parcel.objects.create(
            session_key="test_session",
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )

    def test_parcel_str(self):
        """Проверка строкового представления посылки."""
        self.assertEqual(str(self.parcel), "Тестовая посылка")

    def test_parcel_type_str(self):
        """Проверка строкового представления типа посылки."""
        self.assertEqual(str(self.parcel_type), "Одежда")


class ParcelSerializerTest(TestCase):
    """Тесты для сериализатора ParcelSerializer."""

    def setUp(self):
        self.parcel_type = ParcelType.objects.create(name="Одежда")
        self.parcel_data = {
            "name": "Тестовая посылка",
            "weight": 1.5,
            "type": self.parcel_type.id,
            "value": 100.0
        }
        self.session_key = "test_session"

    def test_valid_data(self):
        """Проверка валидации корректных данных."""
        serializer = ParcelSerializer(data={**self.parcel_data, "session_key": self.session_key})
        self.assertTrue(serializer.is_valid())

    def test_invalid_weight(self):
        """Проверка ошибки при отрицательном весе."""
        invalid_data = {**self.parcel_data, "weight": -1, "session_key": self.session_key}
        serializer = ParcelSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("weight", serializer.errors)

    def test_invalid_value(self):
        """Проверка ошибки при отрицательной стоимости."""
        invalid_data = {**self.parcel_data, "value": -10, "session_key": self.session_key}
        serializer = ParcelSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)


class ParcelAPITest(APITestCase):
    """Тесты для API-роутов."""

    def setUp(self):
        self.client = APIClient()
        self.parcel_type = ParcelType.objects.create(name="Одежда")
        self.client.session.save()
        self.session_key = self.client.session.session_key
        self.client.cookies["sessionid"] = self.session_key
        self.parcel_data = {
            "name": "Тестовая посылка",
            "weight": 1.5,
            "type": self.parcel_type.id,
            "value": 100.0
        }

    def test_register_parcel(self):
        """Проверка регистрации посылки."""
        response = self.client.post(reverse("register_parcel"), self.parcel_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(Parcel.objects.count(), 1)
        parcel = Parcel.objects.first()
        self.assertEqual(parcel.session_key, self.session_key)

    def test_register_parcel_invalid_data(self):
        """Проверка ошибки при неверных данных."""
        invalid_data = {**self.parcel_data, "weight": -1}
        response = self.client.post(reverse("register_parcel"), invalid_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("weight", response.data)

    def test_get_parcel_types(self):
        """Проверка получения списка типов посылок."""
        ParcelType.objects.create(name="Электроника")
        response = self.client.get(reverse("parcel_types"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data["results"][0]["name"], "Одежда")

    def test_get_parcels(self):
        """Проверка получения списка посылок."""
        Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        response = self.client.get(reverse("parcel_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Тестовая посылка")

    def test_get_parcels_filter_by_type(self):
        """Проверка фильтрации посылок по типу."""
        electronics = ParcelType.objects.create(name="Электроника")
        Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка 1",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка 2",
            weight=2.0,
            type=electronics,
            value=200.0
        )
        response = self.client.get(reverse("parcel_list"), {"type": electronics.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["type"], electronics.id)

    def test_get_parcels_filter_by_cost_calculated(self):
        """Проверка фильтрации по наличию стоимости доставки."""
        parcel = Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0,
            delivery_cost=500.0
        )
        Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка 2",
            weight=2.0,
            type=self.parcel_type,
            value=200.0
        )
        response = self.client.get(reverse("parcel_list"), {"cost_calculated": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], parcel.id)

    def test_get_parcel_detail(self):
        """Проверка получения деталей посылки."""
        parcel = Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        response = self.client.get(reverse("parcel_detail", args=[parcel.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Тестовая посылка")

    def test_get_parcel_detail_not_found(self):
        """Проверка ошибки при запросе несуществующей посылки."""
        response = self.client.get(reverse("parcel_detail", args=[999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Посылка не найдена")

    def test_get_parcel_detail_wrong_session(self):
        """Проверка доступа к посылке другой сессии."""
        parcel = Parcel.objects.create(
            session_key="other_session",
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        response = self.client.get(reverse("parcel_detail", args=[parcel.id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Посылка не найдена")


class ParcelWebTest(TestCase):
    """Тесты для веб-интерфейса."""

    def setUp(self):
        self.client = Client()
        self.parcel_type = ParcelType.objects.create(name="Одежда")
        self.client.session.save()
        self.session_key = self.client.session.session_key
        self.client.session.save()
        self.parcel_data = {
            "name": "Тестовая посылка",
            "weight": "1.5",
            "type": str(self.parcel_type.id),
            "value": "100.0"
        }

    def test_register_parcel_web(self):
        """Проверка регистрации посылки через веб-форму."""
        response = self.client.post(reverse("register_parcel_web"), self.parcel_data)
        self.assertEqual(response.status_code, 302)  # Редирект на список посылок
        self.assertEqual(Parcel.objects.count(), 1)
        parcel = Parcel.objects.first()
        self.assertEqual(parcel.session_key, self.session_key)

    def test_register_parcel_web_invalid_data(self):
        """Проверка ошибки при неверных данных в веб-форме."""
        invalid_data = {**self.parcel_data, "weight": "-1"}
        response = self.client.post(reverse("register_parcel_web"), invalid_data)
        self.assertEqual(response.status_code, 200)  # Остается на странице
        self.assertContains(response, "Вес должен быть положительным")
        self.assertEqual(Parcel.objects.count(), 0)

    def test_parcel_list_web(self):
        """Проверка отображения списка посылок."""
        Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        response = self.client.get(reverse("parcel_list_web"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовая посылка")

    def test_parcel_types_web(self):
        """Проверка отображения типов посылок."""
        response = self.client.get(reverse("parcel_types_web"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Одежда")

    def test_parcel_detail_web(self):
        """Проверка отображения деталей посылки."""
        parcel = Parcel.objects.create(
            session_key=self.session_key,
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        response = self.client.get(reverse("parcel_detail_web", args=[parcel.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовая посылка")

    def test_parcel_detail_web_not_found(self):
        """Проверка ошибки при запросе несуществующей посылки."""
        response = self.client.get(reverse("parcel_detail_web", args=[999]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Посылка не найдена")


class DeliveryCostTaskTest(TestCase):
    """Тесты для периодической задачи расчета стоимости доставки."""

    def setUp(self):
        self.parcel_type = ParcelType.objects.create(name="Одежда")
        self.parcel = Parcel.objects.create(
            session_key="test_session",
            name="Тестовая посылка",
            weight=1.5,
            type=self.parcel_type,
            value=100.0
        )
        cache.clear()

    @patch("requests.get")
    def test_calculate_delivery_costs(self, mock_get):
        """Проверка расчета стоимости доставки."""
        mock_get.return_value.json.return_value = {
            "Valute": {"USD": {"Value": 90.0}}
        }
        calculate_delivery_costs()
        self.parcel.refresh_from_db()
        expected_cost = (1.5 * 0.5 + 100.0 * 0.01) * 90.0  # (0.75 + 1.0) * 90 = 157.5
        self.assertEqual(self.parcel.delivery_cost, expected_cost)
        self.assertEqual(cache.get("usd_to_rub"), 90.0)

    @patch("requests.get")
    def test_calculate_delivery_costs_cached_rate(self, mock_get):
        """Проверка использования кэшированного курса."""
        cache.set("usd_to_rub", 80.0, timeout=3600)
        calculate_delivery_costs()
        self.parcel.refresh_from_db()
        expected_cost = (1.5 * 0.5 + 100.0 * 0.01) * 80.0  # (0.75 + 1.0) * 80 = 140.0
        self.assertEqual(self.parcel.delivery_cost, expected_cost)
        mock_get.assert_not_called()


class ExceptionHandlerTest(APITestCase):
    """Тесты для custom_exception_handler."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view = APIView()
        self.logger = logging.getLogger("parcels.exceptions")

    def _create_context(self):
        """Создает тестовый контекст для обработчика исключений."""
        request = self.factory.get("/test/")
        return {"request": request, "view": self.view}

    def test_validation_error_single(self):
        """Проверка обработки ValidationError с одной ошибкой."""
        exception = ValidationError("Неверные данные")
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {
            "status": "error",
            "detail": "Неверные данные",
            "code": 400
        })

    def test_validation_error_multiple(self):
        """Проверка обработки ValidationError с множественными ошибками."""
        exception = ValidationError(["Ошибка 1", "Ошибка 2"])
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {
            "status": "error",
            "detail": "Ошибка 1, Ошибка 2",
            "code": 400
        })
        with patch("parcels.exceptions.logger.error") as mock_logger:
            custom_exception_handler(exception, context)
            mock_logger.assert_called_once_with("Произошла ошибка: Ошибка 1, Ошибка 2")

    def test_not_found_error(self):
        """Проверка обработки NotFound."""
        exception = NotFound("Ресурс не найден")
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {
            "status": "error",
            "detail": "Ресурс не найден",
            "code": 404
        })

    def test_permission_denied_error(self):
        """Проверка обработки PermissionDenied."""
        exception = PermissionDenied("Доступ запрещен")
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {
            "status": "error",
            "detail": "Доступ запрещен",
            "code": 403
        })

    def test_unhandled_exception(self):
        """Проверка обработки непредусмотренного исключения."""
        exception = Exception("Неизвестная ошибка")
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {
            "status": "error",
            "detail": "Неизвестная ошибка",
            "code": 500
        })

    @patch("parcels.exceptions.logger.error")
    def test_logging(self, mock_logger):
        """Проверка логирования ошибки."""
        exception = ValidationError("Ошибка валидации")
        context = self._create_context()
        response = custom_exception_handler(exception, context)
        self.assertEqual(response.status_code, 400)
        mock_logger.assert_called_once_with("Произошла ошибка: Ошибка валидации")

    def test_no_response_exception(self):
        """Проверка обработки исключения, когда стандартный обработчик возвращает None."""
        with patch("rest_framework.views.exception_handler", return_value=None):
            exception = Exception("Необработанное исключение")
            context = self._create_context()
            response = custom_exception_handler(exception, context)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.data, {
                "status": "error",
                "detail": "Необработанное исключение",
                "code": 500
            })
