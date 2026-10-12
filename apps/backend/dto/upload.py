from pydantic import Field, BaseModel
from typing import Optional
from dto import FindDTO


class UploadFileDTO(BaseModel):
    folder: Optional[str] = Field(default="agent")
    tags: Optional[str] = Field(default=None)
    widgetId: Optional[str] = Field(default=None)
    extractFile: Optional[bool] = Field(default=False)
    rescaleFile: Optional[bool] = Field(default=False)
    scaleFactor: Optional[float] = Field(default=None)
    workspaceId: Optional[str] = Field(default=None)
    dashboardId: Optional[str] = Field(default=None)
    connectionId: Optional[str] = Field(default=None)
    filename: Optional[str] = Field(default=None)
    createdBy: str


class UploadFindDTO(FindDTO):
    widgetId: Optional[str] = Field(default=None)
    dashboardId: Optional[str] = Field(default=None)
    tags: Optional[list] = Field(default=None)
