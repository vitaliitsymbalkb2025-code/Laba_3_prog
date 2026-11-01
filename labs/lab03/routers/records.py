"""Маршрути для вимірювань часу опрацювання повідомлень."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Response, status

from .. import repository
from ..config import (
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    SQLITE_INT_MAX,
    VALUE_MAX,
    VALUE_MIN,
    VALUE_UNIT,
)
from ..schemas import RecordBulk, RecordCreate, RecordRead, RecordReplace, Status
from . import RESPONSE_404, RESPONSE_409, to_http_error

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[
    int, Path(gt=0, le=SQLITE_INT_MAX, description="Ідентифікатор запису")
]


@router.get(
    "",
    response_model=list[RecordRead],
    summary="Список вимірювань з фільтрами",
    description=(
        "Фільтри об'єднуються через AND; результат відсортовано за id. "
        "Неіснуюча категорія або відсутність збігів дає порожній список."
    ),
)
def list_records(
    category_id: Annotated[
        int | None,
        Query(gt=0, le=SQLITE_INT_MAX, description="Лише записи цієї категорії"),
    ] = None,
    record_status: Annotated[
        Status | None, Query(alias="status", description="Лише записи з цим статусом")
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=VALUE_MIN,
            le=VALUE_MAX,
            allow_inf_nan=False,
            description=f"Мінімальна тривалість, {VALUE_UNIT} (value >= min_value)",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у title з урахуванням регістру",
        ),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=PAGE_MAX_LIMIT, description="Максимум записів")
    ] = PAGE_DEFAULT_LIMIT,
    offset: Annotated[
        int, Query(ge=0, le=SQLITE_INT_MAX, description="Кількість пропущених")
    ] = 0,
) -> list[dict]:
    """Отримати сторінку записів."""
    return repository.list_records(
        category_id=category_id,
        status=record_status,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити вимірювання",
    responses={**RESPONSE_404, **RESPONSE_409},
)
def create_record(payload: RecordCreate) -> dict:
    """Створити запис; неіснуюча категорія — 404, дублікат code — 409."""
    try:
        return repository.create_record(payload.model_dump())
    except repository.RepositoryError as error:
        raise to_http_error(error) from error


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пакетне створення (атомарно)",
    description=(
        "Приймає JSON-масив від 1 до 100 об'єктів RecordCreate. Усі записи "
        "зберігаються в одній транзакції: за будь-якої помилки жоден не зберігається."
    ),
    responses={**RESPONSE_404, **RESPONSE_409},
)
def create_records_bulk(payload: Annotated[RecordBulk, Body()]) -> list[dict]:
    """Створити пакет записів у одній транзакції."""
    try:
        return repository.create_records_bulk(item.model_dump() for item in payload)
    except repository.RepositoryError as error:
        raise to_http_error(error) from error


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    summary="Отримати вимірювання за id",
    responses=RESPONSE_404,
)
def get_record(record_id: RecordId) -> dict:
    """Отримати один запис."""
    try:
        return repository.get_record(record_id)
    except repository.RepositoryError as error:
        raise to_http_error(error) from error


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    summary="Повністю замінити змінювані поля",
    description="Усі п'ять полів обов'язкові; id запису не змінюється.",
    responses={**RESPONSE_404, **RESPONSE_409},
)
def replace_record(record_id: RecordId, payload: RecordReplace) -> dict:
    """Замінити code, title, category_id, value і status."""
    try:
        return repository.replace_record(record_id, payload.model_dump())
    except repository.RepositoryError as error:
        raise to_http_error(error) from error


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити вимірювання",
    responses=RESPONSE_404,
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис."""
    try:
        repository.delete_record(record_id)
    except repository.RepositoryError as error:
        raise to_http_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
