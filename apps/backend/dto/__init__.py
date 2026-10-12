from typing import Any, Optional
from pydantic import BaseModel, Field
import os
from datetime import datetime


class CustomBaseModel(BaseModel):
    def dict(self, *, include: Any = None, exclude: Any = None, by_alias: bool = False, exclude_unset: bool = True, **kwargs) -> dict:
        return super().dict(include=include, exclude=exclude, by_alias=by_alias, exclude_unset=exclude_unset, **kwargs)


class BaseFindDTO(BaseModel):
    search: str = Field(default=None)
    search_by: list = Field(default=[])
    operator: str = Field(default=None)
    orderBy: str = Field(default="createdAt")
    order: str = Field(default="desc")
    page: int = Field(default=1)
    size: int = Field(default=10)
    searchIgnoreSpecial: bool = Field(default=False)


class FindDTO(BaseFindDTO):
    filters: list = Field(default=[])

class ConnectionFindDTO(FindDTO):
    readWrite: bool = Field(default=False)
    showHost: bool = Field(default=False)

class LogDTO(BaseModel):
    userId: Optional[str] = Field(default=None)
    endpoint: str = Field(default=None)
    metadata: str = Field(default=None)
    executedAt: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    executionTime: int | float = Field(default=None)
    code: int = Field(default=None)
    errorMessage: str = Field(default=None)
