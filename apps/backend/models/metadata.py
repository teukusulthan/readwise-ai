from pydantic import BaseModel
from typing import Optional
from models.pagination import Pagination


class MetadataSuccess(BaseModel):
    pagination: Optional[Pagination] = Pagination()
    status: Optional[bool] = True
    executionTime: int = 0
    responseCode: int = 200
    message: Optional[object] = 'Success'

    class Config:
        extra = "allow"


class MetadataFailed(BaseModel):
    pagination: Optional[Pagination] = Pagination()
    status: Optional[bool] = False
    executionTime: int = 0
    responseCode: int = 400
    message: Optional[str] = 'Failed'

    class Config:
        extra = "allow"
