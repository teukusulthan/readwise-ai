from pydantic import BaseModel, Field, validator
from util.helper import to_snake_case
from typing import Optional
from decimal import Decimal
from config.base import settings
from models.metadata import MetadataSuccess, MetadataFailed
from util.aes_encryption import encrypt_aes_data
from config.base import settings
import json
from loguru import logger


class BaseResponse(BaseModel):
    metaData: MetadataSuccess = Field(default=MetadataSuccess())
    data: object
    additionalInfo: Optional[object] = None
    copyright: Optional[str] = settings.COPYRIGHT

    @staticmethod
    def build_data(data):
        if settings.BASE_RESPONSE_CASE == "snake_case":
            data = to_snake_case(data)
        return data

    @validator("data", pre=True)
    def convert_decimal_to_float(cls, value):
        for item in value:
            if isinstance(item, dict):
                for key, val in item.items():
                    if isinstance(val, Decimal):
                        item[key] = float(val)
        return value

    def model_dump(self, *, mode = 'python', include = None, exclude = None, context = None, by_alias = False, exclude_unset = False, exclude_defaults = False, exclude_none = False, round_trip = False, warnings = True, serialize_as_any = False):
        try:
            if self.data:
                str_data = json.dumps(self.data).encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore')
                self.data = json.loads(str_data)
        except Exception as e:
            logger.error(f"Cannot encode data, caused by: \n{e}")
        original_dict = super().model_dump(mode=mode, include=include, exclude=exclude, context=context, by_alias=by_alias, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none, round_trip=round_trip, warnings=warnings, serialize_as_any=serialize_as_any)
        if settings.ENC_ACTIVE == True:
            original_dict = {"data": encrypt_aes_data(original_dict)}
        return original_dict

    def dict(self, *, include = None, exclude = None, by_alias = False, exclude_unset = False, exclude_defaults = False, exclude_none = False):
        original_dict = super().dict(include=include, exclude=exclude, by_alias=by_alias, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none)
        if settings.ENC_ACTIVE == True:
            original_dict = {"data": encrypt_aes_data(original_dict)}
        return original_dict


class BaseResponseFailed(BaseModel):
    metaData: MetadataFailed = Field(default=MetadataFailed())
    data: Optional[object | str] = None
    additionalInfo: Optional[object] = None
    copyright: Optional[str] = settings.COPYRIGHT

    def model_dump(self, *, mode = 'python', include = None, exclude = None, context = None, by_alias = False, exclude_unset = False, exclude_defaults = False, exclude_none = False, round_trip = False, warnings = True, serialize_as_any = False):
        original_dict = super().model_dump(mode=mode, include=include, exclude=exclude, context=context, by_alias=by_alias, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none, round_trip=round_trip, warnings=warnings, serialize_as_any=serialize_as_any)
        if settings.ENC_ACTIVE == True:
            original_dict = {"data": encrypt_aes_data(original_dict)}
        return original_dict

    def dict(self, *, include = None, exclude = None, by_alias = False, exclude_unset = False, exclude_defaults = False, exclude_none = False):
        original_dict = super().dict(include=include, exclude=exclude, by_alias=by_alias, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none)
        if settings.ENC_ACTIVE == True:
            original_dict = {"data": encrypt_aes_data(original_dict)}
        return original_dict
