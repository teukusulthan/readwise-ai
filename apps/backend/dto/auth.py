from pydantic import BaseModel, Field, model_validator, validator
from typing import Optional
import re
import dns.resolver
import requests
from config.base import settings
from service import Services
import json
from loguru import logger

redis = Services.redis()

class AuthDTO(BaseModel):
    email: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)


class GoogleSSORequest(BaseModel):
    code: str
    redirect_uri: str


class SMTPDTO(BaseModel):
    smtpHost: str
    smtpPort: int
    smtpEmail: str
    smtpSender: Optional[str] = Field(None)
    smtpPassword: Optional[str] = ""
    useTls: Optional[bool] = False
    type: Optional[str] = Field("local")

    @model_validator(mode="after")
    def unknown_sender(self):
        if not self.smtpSender:
            self.smtpSender = self.smtpEmail

        return self


class RegisterDTO(BaseModel):
    fullname: Optional[str] = Field(default=None)
    username: str
    email: str
    password: str
    phone: str
    additional: Optional[dict] = Field(default=None)


    @validator("email")
    def validate_email(cls, email: str):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

        if not cls.has_mx_record(email):
            raise ValueError("Email domain is not valid or cannot receive messages")
        
        if not cls.verify_email(email):
            raise ValueError("Email address is not deliverable or does not exist")

        return email

    @staticmethod
    def has_mx_record(email: str) -> bool:
        domain = email.split('@')[-1]
        try:
            records = dns.resolver.resolve(domain, 'MX')
            return len(records) > 0
        except Exception:
            return False
        
    @staticmethod
    def verify_email(email: str) -> dict:
        params = {
            "api_key": settings.PROOFY_API_KEY,
            "email": email,
        }
        key = f"email_verify:{email}"

        data_redis = redis.get(key)
        if data_redis:
            logger.success(f"Success get data from redis with id {key}")
            data_redis = json.loads(data_redis)
            return data_redis.get("status") == "valid"

        try:
            response = requests.get(settings.PROOFY_URL, params=params)
            result = response.json()

            if response.status_code > 300:
                raise Exception(f"Email verification failed. {result.get('message')}")

            redis.set(
                f"email_verify:{email}",
                json.dumps(result),
                2592000,
            )
            logger.success(f"Success set data to redis with id {key}")

            return result.get("status") == "valid"
        except Exception:
            raise Exception("Email verification failed")
class RequestChangeDTO(BaseModel):
    email: str

    @validator("email")
    def validate_email(cls, email: str):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

        if not cls.has_mx_record(email):
            raise ValueError("Email domain is not valid or cannot receive messages")

        return email

    @staticmethod
    def has_mx_record(email: str) -> bool:
        domain = email.split('@')[-1]
        try:
            records = dns.resolver.resolve(domain, 'MX')
            return len(records) > 0
        except Exception:
            return False
        
class RequestVerifyEmailDTO(BaseModel):
    email: str

    @validator("email")
    def validate_email(cls, email: str):
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

        if not cls.has_mx_record(email):
            raise ValueError("Email domain is not valid or cannot receive messages")

        return email

    @staticmethod
    def has_mx_record(email: str) -> bool:
        domain = email.split('@')[-1]
        try:
            records = dns.resolver.resolve(domain, 'MX')
            return len(records) > 0
        except Exception:
            return False
        
    @staticmethod
    def verify_email(email: str) -> dict:
        params = {
            "api_key": settings.PROOFY_API_KEY,
            "email": email,
        }

        key = f"email_verify:{email}"

        data_redis = redis.get(key)
        if data_redis:
            logger.success(f"Success get data from redis with id {key}")
            data_redis = json.loads(data_redis)
            return data_redis.get("status") == "valid"

        try:
            response = requests.get(settings.PROOFY_URL, params=params)
            result = response.json()

            if response.status_code > 300:
                raise Exception(f"Email verification failed. {result.get('message')}")

            redis.set(
                f"email_verify:{email}",
                json.dumps(result),
                2592000,
            )
            logger.success(f"Success set data to redis with id {key}")

            return result.get("status") == "valid"
        except Exception:
            raise Exception("Email verification failed")


class ChangePasswordDTO(BaseModel):
    newPassword: str
    token: str


class ChangePasswordOTPDTO(BaseModel):
    newPassword: str
    otp: str


class OtpDTO(BaseModel):
    otp: str
    email: str

class VerifyEmailDTO(BaseModel):
    url: str
    email: str


class RegisterOTPDTO(RegisterDTO):
    otp: str

class GenerateTwoFactorDTO(BaseModel):
    email: str
    password: str
    type: str # email | google_authenticator

class TwoFactorVerifyDTO(BaseModel):
    session_token: str
    otp: str

class TwoFactorResendDTO(BaseModel):
    session_token: str
