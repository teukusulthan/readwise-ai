from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatAskDTO(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # Restrict answering to these books. Omit to use every indexed book.
    bookIds: Optional[List[str]] = Field(default=None, max_length=50)
    topK: Optional[int] = Field(default=None, ge=1, le=12)
    # /chat/stream only: continue this saved conversation. Omit to start a new one.
    conversationId: Optional[str] = Field(default=None, max_length=64)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank.")
        return value.strip()
