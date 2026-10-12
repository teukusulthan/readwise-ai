from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SearchQueryDTO(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    # Restrict to these books. Omit to search every indexed book.
    bookIds: Optional[List[str]] = Field(default=None, max_length=50)
    topK: Optional[int] = Field(default=None, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must not be blank.")
        return value.strip()
