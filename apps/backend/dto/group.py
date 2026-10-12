from pydantic import Field, BaseModel
from typing import Optional, List, Dict


class GroupDTO(BaseModel):
    parentId: Optional[str] = Field(default=None)
    settings: Optional[dict] = Field(default=None)
    filters: Optional[List[Dict]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    image: Optional[str] = Field(default=None)
    personalization : Optional[dict] = Field(default=None)


class UpdateGroupDTO(GroupDTO):
    id: str
