"""Маршрути для категорій (джерел повідомлень)."""

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from .. import repository
from ..schemas import CategoryCreate, CategoryRead
from . import RESPONSE_404, RESPONSE_409, to_http_error

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[int, Path(gt=0, description="Ідентифікатор категорії")]


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Список категорій",
    description="Повертає всі категорії за зростанням id.",
)
def list_categories() -> list[dict]:
    """Отримати список категорій."""
    return repository.list_categories()


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити категорію",
    responses=RESPONSE_409,
)
def create_category(payload: CategoryCreate) -> dict:
    """Створити категорію; дублікат назви повертає 409."""
    try:
        return repository.create_category(payload.name)
    except repository.RepositoryError as error:
        raise to_http_error(error) from error


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити порожню категорію",
    description="Категорію з записами видалити не можна (409).",
    responses={**RESPONSE_404, **RESPONSE_409},
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію без записів."""
    try:
        repository.delete_category(category_id)
    except repository.RepositoryError as error:
        raise to_http_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
