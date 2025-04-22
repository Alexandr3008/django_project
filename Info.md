Описание проекта
Проект представляет собой веб-приложение на базе Django и Django REST Framework, реализующее API для управления посылками (Parcels). Основные функции включают создание, получение и удаление посылок, расчёт стоимости доставки с использованием внешнего API валютных курсов, а также обработку ошибок с помощью пользовательского обработчика исключений. Проект использует PostgreSQL в качестве базы данных, Redis для кэширования, Celery для асинхронных задач и Docker для контейнеризации. Ведение журнала настроено для записи ошибок в файл delivery_service.log.

Основные компоненты:

Модели: Parcel (посылка) и ParcelType (тип посылки).
API: Конечные точки для работы с посылками (/parcels/, /parcels/<id>/).
Сериализаторы: ParcelSerializer для преобразования данных.
Задачи: Периодическая задача calculate_delivery_costs для расчета стоимости доставки на основе курса USD.
Обработка ошибок: пользовательский обработчик исключений (custom_exception_handler) для стандартизации ответов API.
Тесты: юнит-тесты для моделей, сериализаторов, API, задач и обработчика исключений.
Проект использует Poetry для управления зависимостями и Docker Compose для запуска сервисов (веб-приложение, база данных, Redis, Celery).


Порядок действий для запуска проекта:

1. Склонируйте репозиторий проекта на локальную машину:
git clone https://github.com/Alexandr3008/django_project

2. Выполните эти команды в терминале:
poetry install --only main --no-root  
poetry run python manage.py collectstatic

3. Создайте файл .env: в корневом каталоге проекта создайте файл .env с переменными окружения. Пример:
SECRET_KEY=secret-key
DEBUG=True
POSTGRES_DB=delivery_service
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

4. Выполните команду для сборки и запуска контейнеров:
docker-compose up --build

5. Примените миграции: в новом терминале выполните миграции для создания таблиц в базе данных:
docker-compose exec web poetry run python manage.py migrate
Загрузите начальные данные для добавления категорий в таблице ParcelType:
docker-compose exec web poetry run python manage.py seed_parcel_types

6. Запустите тесты:
docker-compose exec web poetry run python manage.py test 
Эта команда запустит все тесты из parcels/tests.py

7. Проверьте доступность API: откройте браузер или используйте curl/Postman для проверки конечных точек:
Создание посылки: POST http://localhost:8000/parcels/
Получение списка посылок: GET http://localhost:8000/parcels/
Получение сведений о посылке: GET http://localhost:8000/parcels/<идентификатор>/
