"""Pagination contract shared by every list endpoint: {items, total, page, size}."""

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[int, Query(ge=1, description="Página (desde 1)")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Elementos por página")] = 20,
) -> PageParams:
    return PageParams(page=page, size=size)


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
