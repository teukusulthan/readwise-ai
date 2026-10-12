from pydantic import Field, BaseModel
from typing import List, Optional
from dto import FindDTO


class UserDTO(BaseModel):
    createdBy: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)
    fullname: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    permissionId: Optional[str] = Field(default=None)
    about: Optional[str] = Field(default=None)
    dateOfBirth: Optional[int] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    lastActive: Optional[int] = Field(default=None)
    expiredDate: Optional[int] = Field(default=None)
    phone: str
    groupId: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    image: Optional[str] = Field(default=None)
    multiLogin: Optional[bool] = Field(default=None)
    emailVerified: Optional[bool] = Field(default=None)
    address: Optional[dict] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    additional: Optional[dict] = Field(default=None)

class UpdateUserDTO(UserDTO):
    id: str


class ResetPasswordDTO(BaseModel):
    id: str
    password: str


class FindUserDTO(FindDTO):
    online: Optional[bool] = Field(default=None)
    
class DeleteBody(BaseModel):
    password: str
