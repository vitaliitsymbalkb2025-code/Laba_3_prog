"""Pydantic-моделі запитів і відповідей для варіанта 9."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import (
    BULK_MAX_ITEMS,
    BULK_MIN_ITEMS,
    SQLITE_INT_MAX,
    VALUE_MAX,
    VALUE_MIN,
    VALUE_UNIT,
)

Status = Literal["new", "in_progress", "done"]


class CategoryCreate(BaseModel):
    """Дані для створення категорії (джерела повідомлень)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(
        min_length=2,
        max_length=40,
        description="Назва джерела повідомлень, наприклад siem",
        examples=["soc_mail"],
    )


class CategoryRead(BaseModel):
    """Категорія, повернена API."""

    id: int = Field(gt=0)
    name: str


class RecordCreate(BaseModel):
    """Дані для створення вимірювання часу опрацювання."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(
        min_length=3,
        max_length=40,
        description="Унікальний код вимірювання",
        examples=["V09-TEST"],
    )
    title: str = Field(
        min_length=3,
        max_length=120,
        description="Назва вимірювання",
        examples=["Вимірювання опрацювання тестове"],
    )
    category_id: int = Field(
        gt=0,
        le=SQLITE_INT_MAX,
        strict=True,
        description="Ідентифікатор наявної категорії",
        examples=[1],
    )
    value: float = Field(
        ge=VALUE_MIN,
        le=VALUE_MAX,
        allow_inf_nan=False,
        strict=True,
        description=f"Тривалість опрацювання, {VALUE_UNIT}; скінченне число >= 0",
        examples=[12.5],
    )
    status: Status = Field(
        description="Стан перевірки вимірювання",
        examples=["new"],
    )


class RecordReplace(RecordCreate):
    """Повна заміна всіх змінюваних полів запису (для PUT)."""


class RecordRead(BaseModel):
    """Вимірювання разом з ідентифікатором і назвою категорії."""

    id: int
    code: str
    title: str
    category_id: int
    category_name: str
    value: float
    status: Status


RecordBulk = Annotated[
    list[RecordCreate],
    Field(min_length=BULK_MIN_ITEMS, max_length=BULK_MAX_ITEMS),
]


class ErrorResponse(BaseModel):
    """Тіло відповіді з описом очікуваної помилки."""

    detail: str


class PingResponse(BaseModel):
    """Відповідь перевірки доступності."""

    status: Literal["ok"]


class StudentResponse(BaseModel):
    """Дані студента з shared/student.py."""

    student_name: str
    group_name: str
    variant_number: int
