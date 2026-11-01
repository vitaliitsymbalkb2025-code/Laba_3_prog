"""Параметризовані SQL-операції над таблицями categories і records.

Модуль не залежить від FastAPI: помилки даних повертаються як власні винятки,
а шар API перетворює їх на HTTP-відповіді.
"""

import logging
import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from typing import Any

from .database import get_connection

logger = logging.getLogger(__name__)

RECORD_SELECT = """
    SELECT r.id, r.code, r.title, r.category_id, c.name AS category_name,
           r.value, r.status
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class RepositoryError(Exception):
    """Базова помилка шару доступу до даних."""


class NotFoundError(RepositoryError):
    """Запис або категорію не знайдено."""


class ConflictError(RepositoryError):
    """Порушено унікальність або зв'язки між таблицями."""


class ConstraintError(RepositoryError):
    """Дані не пройшли перевірку обмежень бази."""


def _connect() -> sqlite3.Connection:
    """Відкрити з'єднання, яке повертає рядки як словникоподібні об'єкти."""
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    return connection


def _translate_integrity_error(error: sqlite3.IntegrityError) -> RepositoryError:
    """Перетворити IntegrityError SQLite на зрозумілий виняток репозиторію."""
    message = str(error)
    logger.warning("Порушення обмеження SQLite: %s", message)
    if "UNIQUE" in message:
        return ConflictError("Значення унікального поля вже існує")
    if "FOREIGN KEY" in message:
        return NotFoundError("Категорію не знайдено")
    return ConstraintError("Дані не відповідають обмеженням бази")


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    """Перевірити наявність категорії в межах поточного з'єднання."""
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> dict[str, Any]:
    """Прочитати один запис із назвою категорії через JOIN."""
    row = connection.execute(RECORD_SELECT + " WHERE r.id = ?", (record_id,)).fetchone()
    if row is None:
        raise NotFoundError("Запис не знайдено")
    return dict(row)


def _record_params(data: Mapping[str, Any]) -> tuple[Any, ...]:
    """Сформувати кортеж параметрів у фіксованому порядку полів."""
    return (
        data["code"],
        data["title"],
        data["category_id"],
        data["value"],
        data["status"],
    )


# --- Категорії ---------------------------------------------------------------


def list_categories() -> list[dict[str, Any]]:
    """Повернути всі категорії за зростанням id."""
    with closing(_connect()) as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> dict[str, Any]:
    """Створити категорію; id генерує SQLite."""
    with closing(_connect()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError as error:
            raise _translate_integrity_error(error) from error
        return {"id": cursor.lastrowid, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити категорію, лише якщо вона не містить записів."""
    with closing(_connect()) as connection:
        try:
            with connection:
                if not _category_exists(connection, category_id):
                    raise NotFoundError("Категорію не знайдено")
                used = connection.execute(
                    "SELECT COUNT(*) FROM records WHERE category_id = ?",
                    (category_id,),
                ).fetchone()[0]
                if used:
                    raise ConflictError("Категорія містить записи")
                connection.execute(
                    "DELETE FROM categories WHERE id = ?", (category_id,)
                )
        except sqlite3.IntegrityError as error:
            raise ConflictError("Категорія містить записи") from error


# --- Записи --------------------------------------------------------------------


def create_record(data: Mapping[str, Any]) -> dict[str, Any]:
    """Додати один запис і повернути його разом із category_name."""
    with closing(_connect()) as connection:
        try:
            with connection:
                if not _category_exists(connection, data["category_id"]):
                    raise NotFoundError("Категорію не знайдено")
                cursor = connection.execute(
                    "INSERT INTO records (code, title, category_id, value, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    _record_params(data),
                )
        except sqlite3.IntegrityError as error:
            raise _translate_integrity_error(error) from error
        return _fetch_record(connection, cursor.lastrowid)


def get_record(record_id: int) -> dict[str, Any]:
    """Повернути запис за id або підняти NotFoundError."""
    with closing(_connect()) as connection:
        return _fetch_record(connection, record_id)


def list_records(
    *,
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Повернути записи з фільтрами, об'єднаними через AND, і пагінацією."""
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)

    sql = RECORD_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend((limit, offset))

    with closing(_connect()) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def replace_record(record_id: int, data: Mapping[str, Any]) -> dict[str, Any]:
    """Повністю замінити змінювані поля запису; id не змінюється."""
    with closing(_connect()) as connection:
        try:
            with connection:
                exists = connection.execute(
                    "SELECT 1 FROM records WHERE id = ?", (record_id,)
                ).fetchone()
                if exists is None:
                    raise NotFoundError("Запис не знайдено")
                if not _category_exists(connection, data["category_id"]):
                    raise NotFoundError("Категорію не знайдено")
                connection.execute(
                    "UPDATE records SET code = ?, title = ?, category_id = ?, "
                    "value = ?, status = ? WHERE id = ?",
                    (*_record_params(data), record_id),
                )
        except sqlite3.IntegrityError as error:
            raise _translate_integrity_error(error) from error
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис або підняти NotFoundError, якщо його немає."""
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM records WHERE id = ?", (record_id,)
            )
        if cursor.rowcount == 0:
            raise NotFoundError("Запис не знайдено")


def create_records_bulk(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Додати пакет записів атомарно: або всі, або жодного."""
    items = list(items)
    with closing(_connect()) as connection:
        try:
            with connection:
                created_ids: list[int] = []
                for index, data in enumerate(items, start=1):
                    if not _category_exists(connection, data["category_id"]):
                        raise NotFoundError(
                            f"Елемент пакета {index}: категорію не знайдено"
                        )
                    cursor = connection.execute(
                        "INSERT INTO records (code, title, category_id, value, status) "
                        "VALUES (?, ?, ?, ?, ?)",
                        _record_params(data),
                    )
                    created_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise _translate_integrity_error(error) from error
        return [_fetch_record(connection, record_id) for record_id in created_ids]


# --- Початкове заповнення ------------------------------------------------------


def count_rows() -> tuple[int, int]:
    """Повернути кількість категорій і записів."""
    with closing(_connect()) as connection:
        categories = connection.execute("SELECT COUNT(*) FROM categories").fetchone()
        records = connection.execute("SELECT COUNT(*) FROM records").fetchone()
    return categories[0], records[0]


def seed_initial_data(
    categories: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
) -> bool:
    """Заповнити порожню базу в одній транзакції.

    Повертає False, якщо база вже містить дані (нічого не змінюється).
    """
    with closing(_connect()) as connection:
        try:
            with connection:
                has_data = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM categories) "
                    "OR EXISTS (SELECT 1 FROM records)"
                ).fetchone()[0]
                if has_data:
                    return False
                connection.executemany(
                    "INSERT INTO categories (id, name) VALUES (?, ?)",
                    [(item["id"], item["name"]) for item in categories],
                )
                connection.executemany(
                    "INSERT INTO records (code, title, category_id, value, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [_record_params(item) for item in records],
                )
        except sqlite3.IntegrityError as error:
            raise _translate_integrity_error(error) from error
    return True
