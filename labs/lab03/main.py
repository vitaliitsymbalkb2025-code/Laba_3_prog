"""FastAPI-застосунок ЛР №3: облік часу опрацювання повідомлень (варіант 9)."""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

from .config import APP_TITLE, SUBJECT_AREA, VALUE_THRESHOLD, VALUE_UNIT
from .database import initialize_database
from .routers import categories, records
from .schemas import PingResponse, StudentResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DESCRIPTION = f"""
{SUBJECT_AREA}

* **Одиниця вимірювання `value`:** `{VALUE_UNIT}` (хвилини), скінченне число `>= 0`.
* **Поріг реагування:** `{VALUE_THRESHOLD}` хв. Вимірювання на рівні порогу
  або вище вибирає фільтр `GET /records?min_value={VALUE_THRESHOLD}`.
* **Статуси:** `new`, `in_progress`, `done`.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску, не змінюючи наявних даних."""
    initialize_database()
    logger.info("Базу даних ініціалізовано")
    yield


app = FastAPI(
    title=APP_TITLE,
    description=DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    """Повернути 422 лише з типом, місцем і текстом помилки.

    Вхідне значення не повертається: воно може бути нескінченністю (1e999),
    яку неможливо серіалізувати в JSON, або великим фрагментом тіла запиту.
    """
    details = [
        {"type": item["type"], "loc": list(item["loc"]), "msg": item["msg"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(sqlite3.Error)
async def database_error_handler(_: Request, error: sqlite3.Error) -> JSONResponse:
    """Записати технічну помилку в журнал і повернути клієнту загальне повідомлення."""
    logger.exception("Помилка бази даних: %s", error)
    return JSONResponse(
        status_code=500, content={"detail": "Внутрішня помилка роботи з базою даних"}
    )


@app.get("/ping", response_model=PingResponse, tags=["service"], summary="Перевірка")
def ping() -> dict[str, str]:
    """Перевірити доступність API."""
    return {"status": "ok"}


@app.get(
    "/student",
    response_model=StudentResponse,
    tags=["service"],
    summary="Дані студента",
)
def student() -> dict[str, str | int]:
    """Повернути ПІБ, групу та номер варіанта з shared/student.py."""
    return {
        "student_name": STUDENT_NAME,
        "group_name": GROUP_NAME,
        "variant_number": VARIANT_NUMBER,
    }
