from pydantic import BaseModel, Field, field_validator, model_validator, validator
from typing import Optional
import re
import dns.resolver
import requests
from config.base import settings
from service import Services
import json
from loguru import logger

redis = Services.redis()

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Letters, digits, dots, dashes, underscores; at least one letter, so a username can never equal a phone
# number or an email (login matches the identifier against all three).
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{3,40}")
PHONE_PATTERN = re.compile(r"\+?[0-9]{6,20}")
OTP_PATTERN = r"^[0-9]{6}$"

PASSWORD_MIN_LENGTH = 8
# bcrypt only reads the first 72 bytes: longer passwords would be silently cut.
PASSWORD_MAX_BYTES = 72
# The most common passwords of 8+ characters; the rest of the policy is length (NIST SP 800-63B).
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password12", "password123", "passw0rd", "12345678", "123456789", "1234567890",
    "123123123", "11111111", "00000000", "87654321", "qwertyui", "qwerty123", "qwertyuiop", "1q2w3e4r",
    "1qaz2wsx", "abcd1234", "abc12345", "iloveyou", "sunshine", "princess", "football", "baseball",
    "welcome1", "letmein1", "superman", "trustno1", "admin123", "changeme",
})


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    """`+62 812-3456 (7890)` -> `+6281234567890`: one stored form, so uniqueness and login match."""
    return re.sub(r"[\s()-]", "", value.strip())


def password_problem(password: str, *, username: Optional[str] = None, email: Optional[str] = None) -> Optional[str]:
    """Why `password` is refused, or None when it is acceptable."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Password must be at most {PASSWORD_MAX_BYTES} bytes"
    lowered = password.lower()
    personal = {value.lower() for value in (username, email, (email or "").split("@")[0]) if value}
    if lowered in COMMON_PASSWORDS or lowered in personal:
        return "Password is too easy to guess; choose a less common one"
    return None


def _check_email_format(email: str) -> str:
    email = normalize_email(email)
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Invalid email format")
    return email


class AuthDTO(BaseModel):
    # `email` also matches the username or the phone number.
    email: Optional[str] = Field(default=None, max_length=254)
    password: Optional[str] = Field(default=None, max_length=256)


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
    fullname: Optional[str] = Field(default=None, max_length=120)
    username: str
    email: str
    password: str = Field(max_length=256)
    phone: str

    @field_validator("fullname")
    @classmethod
    def validate_fullname(cls, fullname: Optional[str]):
        if fullname is None:
            return None
        fullname = fullname.strip()
        if any(not char.isprintable() for char in fullname):
            raise ValueError("Full name contains invalid characters")
        return fullname or None

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str):
        username = username.strip()
        if not USERNAME_PATTERN.fullmatch(username) or not re.search(r"[A-Za-z]", username):
            raise ValueError("Username must be 3-40 letters, digits, dots, dashes or underscores, with at least one letter")
        return username

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, phone: str):
        phone = normalize_phone(phone)
        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Enter a valid phone number")
        return phone

    @model_validator(mode="after")
    def validate_password(self):
        problem = password_problem(self.password, username=self.username, email=self.email)
        if problem:
            raise ValueError(problem)
        return self

    @validator("email")
    def validate_email(cls, email: str):
        email = _check_email_format(email)

        # BE_AUTH_EMAIL_VERIFICATION=false (development): no DNS / Proofy deliverability lookups.
        if not settings.AUTH_EMAIL_VERIFICATION:
            return email

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
        email = _check_email_format(email)

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
        email = _check_email_format(email)

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
    email: str
    otp: str = Field(pattern=OTP_PATTERN)
    newPassword: str = Field(max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str):
        return _check_email_format(email)

    @model_validator(mode="after")
    def validate_password(self):
        problem = password_problem(self.newPassword, email=self.email)
        if problem:
            raise ValueError(problem)
        return self


class EmailOtpDTO(BaseModel):
    """Body of POST /auth/verification and /auth/forgot-password/verify: a code is only valid for its email."""
    email: str
    otp: str = Field(pattern=OTP_PATTERN)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str):
        return _check_email_format(email)


class VerifyEmailDTO(BaseModel):
    url: str
    email: str

class GenerateTwoFactorDTO(BaseModel):
    email: str
    password: str
    type: str # email | google_authenticator

class TwoFactorVerifyDTO(BaseModel):
    session_token: str
    otp: str

class TwoFactorResendDTO(BaseModel):
    session_token: str
