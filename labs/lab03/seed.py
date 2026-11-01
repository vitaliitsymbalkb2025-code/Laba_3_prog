"""Початкове заповнення бази навчальними даними варіанта 9 з data/seed.json."""

import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import repository
from .database import DATABASE_PATH, initialize_database
from .schemas import RecordCreate

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"
EXPECTED_CATEGORIES = 3
EXPECTED_RECORDS = 8

logger = logging.getLogger(__name__)


class SeedCategory(BaseModel):
    """Категорія з JSON: id задається явно."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: int = Field(gt=0, strict=True)
    name: str = Field(min_length=2, max_length=40)


class SeedFile(BaseModel):
    """Структура seed.json: два масиви — categories і records."""

    model_config = ConfigDict(extra="forbid")

    categories: list[SeedCategory]
    records: list[RecordCreate]


class SeedDataError(ValueError):
    """Початкові дані некоректні."""


def load_seed(path: Path = SEED_PATH) -> SeedFile:
    """Прочитати JSON і перевірити його структуру та узгодженість."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SeedDataError(f"Не вдалося прочитати файл {path.name}") from error
    except json.JSONDecodeError as error:
        raise SeedDataError(
            f"Некоректний JSON у {path.name}: рядок {error.lineno}"
        ) from error

    try:
        seed = SeedFile.model_validate(raw)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        raise SeedDataError(f"Помилка в полі {location}: {first['msg']}") from error

    if len(seed.categories) != EXPECTED_CATEGORIES:
        raise SeedDataError(f"Очікується {EXPECTED_CATEGORIES} категорії")
    if len(seed.records) != EXPECTED_RECORDS:
        raise SeedDataError(f"Очікується {EXPECTED_RECORDS} записів")

    category_ids = [category.id for category in seed.categories]
    names = [category.name for category in seed.categories]
    codes = [record.code for record in seed.records]
    if len(set(category_ids)) != len(category_ids) or len(set(names)) != len(names):
        raise SeedDataError("Ідентифікатори та назви категорій мають бути унікальні")
    if len(set(codes)) != len(codes):
        raise SeedDataError("Коди записів мають бути унікальні")
    unknown = {r.category_id for r in seed.records} - set(category_ids)
    if unknown:
        raise SeedDataError(f"Записи посилаються на неіснуючі категорії: {unknown}")
    return seed


def main() -> int:
    """Створити таблиці та заповнити порожню базу; повернути код завершення."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        seed = load_seed()
        initialize_database()
        inserted = repository.seed_initial_data(
            [c.model_dump() for c in seed.categories],
            [r.model_dump() for r in seed.records],
        )
    except SeedDataError as error:
        logger.error("Початкові дані некоректні: %s. Базу не змінено.", error)
        return 1
    except repository.RepositoryError as error:
        logger.error("Пакет не збережено, транзакцію скасовано: %s.", error)
        return 1
    except sqlite3.Error:
        logger.exception("Помилка роботи з базою даних")
        return 1

    categories, records = repository.count_rows()
    if inserted:
        logger.info("Базу заповнено: %s", DATABASE_PATH.name)
    else:
        logger.info("База вже містить дані — заповнення пропущено, дані не змінено.")
    logger.info("У базі: категорій — %d, записів — %d.", categories, records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
