from pydantic import Field, BaseModel
from typing import Optional
from enum import Enum


class RoleDTO(BaseModel):
    createdBy: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    rolePosition: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    alias: Optional[str] = Field(default=None)
    parentId: Optional[str] = Field(default=None)
    workspaceId: Optional[str] = Field(default=None)
    organizationId: Optional[str] = Field(default=None)


class UpdateRoleDTO(RoleDTO):
    id: str


