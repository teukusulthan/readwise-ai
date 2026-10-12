from pydantic import Field, BaseModel
from typing import Optional


class PermissionDTO(BaseModel):
    createdBy: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    privileges: Optional[list | dict] = Field(default=None)
    type: Optional[str] = Field(default=None)
    alias: Optional[str] = Field(default=None)
    parentId: Optional[str] = Field(default=None)
    image: Optional[str] = Field(default=None)


class UpdatePermissionDTO(PermissionDTO):
    id: str
