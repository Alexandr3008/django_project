import logging

from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Стандартизация обработки ошибок."""
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict):
            if "detail" in response.data:
                detail = response.data["detail"]
                if isinstance(detail, ErrorDetail):
                    detail = str(detail)
            else:
                detail = []
                for field, errors in response.data.items():
                    if isinstance(errors, list):
                        detail.extend(str(error) for error in errors)
                    else:
                        detail.append(str(errors))
                detail = ", ".join(detail) if detail else "Ошибка валидации данных"
        else:
            detail = ", ".join(str(item) for item in response.data) if isinstance(response.data, list) else str(
                response.data)

        response.data = {
            "status": "error",
            "detail": detail,
            "code": response.status_code
        }
    else:
        # Непредусмотренные исключения
        detail = str(exc) if str(exc) else "Внутренняя ошибка сервера"
        response = Response(
            {
                "status": "error",
                "detail": detail,
                "code": 500
            },
            status=500
        )

    # Формируем сообщение для логирования
    log_message = str(exc)
    if isinstance(exc, ValidationError):
        match exc.detail:
            case list():
                log_message = ", ".join(str(item) for item in exc.detail)
            case ErrorDetail():
                log_message = str(exc.detail)
            case dict():
                log_message = ", ".join(
                    str(error)
                    for errors in exc.detail.values()
                    for error in (errors if isinstance(errors, list) else [errors])
                )

    logger.error(f"Произошла ошибка: {log_message}")

    return response
