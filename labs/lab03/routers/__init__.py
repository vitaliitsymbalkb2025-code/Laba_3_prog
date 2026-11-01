"""Маршрути API та перетворення помилок репозиторію на HTTP-відповіді."""

from fastapi import HTTPException, status

from ..repository import (
    ConflictError,
    ConstraintError,
    NotFoundError,
    RepositoryError,
)
from ..schemas import ErrorResponse

RESPONSE_404 = {404: {"model": ErrorResponse, "description": "Не знайдено"}}
RESPONSE_409 = {409: {"model": ErrorResponse, "description": "Конфлікт даних"}}


def to_http_error(error: RepositoryError) -> HTTPException:
    """Перетворити виняток шару даних на HTTPException з безпечним текстом."""
    if isinstance(error, NotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        code = status.HTTP_409_CONFLICT
    elif isinstance(error, ConstraintError):
        code = 422
    else:
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=code, detail=str(error))
