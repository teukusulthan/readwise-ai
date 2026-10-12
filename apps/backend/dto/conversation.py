from pydantic import BaseModel, Field, field_validator


class RenameConversationDTO(BaseModel):
    id: str = Field(max_length=64)
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title must not be blank.")
        return value
