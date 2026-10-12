# -*- coding: utf-8 -*-
import time
import bcrypt
import json
from hashlib import md5
from smtplib import SMTP
from loguru import logger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from service import BaseMongoRepository
from auth.auth_handler import (
    sign_jwt,
    create_otp,
    token_response,
    decode_jwt,
    create_email_link_verification,
    create_token
)
from config.base import settings
from util.helper import encrypt
from datetime import datetime
from dto.auth import (
    AuthDTO,
    SMTPDTO,
    OtpDTO,
    RequestChangeDTO,
    ChangePasswordOTPDTO,
    RegisterDTO,
    RegisterOTPDTO,
    GoogleSSORequest,
    VerifyEmailDTO,
    RequestVerifyEmailDTO,
    GenerateTwoFactorDTO,
    TwoFactorVerifyDTO,
    TwoFactorResendDTO,
)
from dto.user import UserDTO
from service import Services
from service.user import User
from service.permission import Permission
from service.group import Group
import requests
from authlib.integrations.starlette_client import OAuth


# Error messages
class AuthErrors:
    EMAIL_REQUIRED = "Email cannot be empty"
    INCORRECT_CREDENTIALS = "Incorrect email or password"
    NO_LOGIN_ACCESS = "User doesn't have login access"
    ACCOUNT_EXPIRED = "Account has been expired"
    ACCOUNT_BLOCKED = "Account has been blocked"
    ACCOUNT_DELETED = "Account has been deleted"


class MailSender:

    server: SMTP

    def __init__(self, meta: SMTPDTO) -> None:
        self.meta: SMTPDTO = meta

    def connect(self):
        """
        Establish a connection to the SMTP server.

        :param use_tls: Whether to use a secure connection (TLS).
        :param need_auth: Whether to use authentication (login).
        """
        self.server = SMTP(self.meta.smtpHost, self.meta.smtpPort, timeout=10)
        if self.meta.useTls:
            self.server.starttls()
        if self.meta.type == "google":
            self.server.login(self.meta.smtpEmail, self.meta.smtpPassword)

    def close(self):
        """
        Close the connection to the SMTP server.

        This method is a no-op if the connection is already closed.
        """
        if hasattr(self, "server") and self.server:
            self.server.quit()


class Auth(BaseMongoRepository):
    def __init__(self):
        super().__init__()

        self.mongo = Services.mongo()
        self.redis = Services.redis()
        self.collection = self.get_collection(settings.MONGO_COLLECTION_USER)
        
        self.user_service = User()
        self.group_service = Group()
        self.permission_service = Permission()
        self.smtp_email = settings.SMTP_EMAIL
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.smtp_type = settings.SMTP_TYPE
        self.smtp_sender = settings.SMTP_SENDER

        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.oauth = OAuth()
            self.oauth.register(
                name="google",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                authorize_url="https://accounts.google.com/o/oauth2/auth",
                authorize_params={"scope": "openid email profile"},
                access_token_url="https://oauth2.googleapis.com/token",
                client_kwargs={"scope": "openid email profile"},
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
            )


    def handle_login_fail(self, account_id: str):
        key = f"login_fail:{account_id}"
        login_count = self.redis.incr(key)
        if login_count == 1:
            self.redis.expire(key, settings.ACCOUNT_LOCK_TIME)

        if login_count >= settings.ACCOUNT_FAIL_LIMIT:
            self.redis.set(f"login_lock:{account_id}", "1", ex=settings.ACCOUNT_LOCK_TIME)

    def check_account_lock(self, account_id: str):
        locked = self.redis.get(f"login_lock:{account_id}")
        if locked:
            raise Exception("Account temporarily locked due to multiple failed login attempts. Please wait a few minutes before logging in again.")

    def check_limit_forgot_password(self, account_id: str):
        key = f"forgot_password:account:{account_id}"
        count = self.redis.incr(key)

        if count == 1:
            self.redis.expire(key, settings.ACCOUNT_LOCK_TIME)

        if count > 3:
            raise Exception("Too many password reset attempts. Please wait a few minutes before requesting another reset.")

    def check_forgot_password_cooldown(self, account_id: str):
        key = f"forgot_password:cooldown:{account_id}"

        exists = self.redis.exists(key)

        if exists:
            raise Exception("Please wait before requesting again")

        self.redis.set(key, "1", ex=60)

    def get_user_properties(
        self, dto: AuthDTO, query: dict, validate_password: bool = True
    ):
        account = self.collection.find_one(query)

        if not account:
            raise Exception(f"Incorrect email or password")
        else:
            account_id = account.get("_id")
            self.check_account_lock(account_id)

            expired_date = account.get("expiredDate", None)
            if expired_date not in [None, "", 0]:
                current_time = int(datetime.now().timestamp() * 1000)
                if current_time > expired_date:
                    raise Exception("Account has been expired")

            account_status = account.get("status")
            if account_status in ["deleted", "blocked"]:
                raise Exception(f"Account has been {account_status}")

            if validate_password:
                if not bcrypt.checkpw(
                    dto.password.encode("utf-8"), account["password"].encode("utf-8")
                ):
                    self.handle_login_fail(account_id)
                    raise Exception(f"Incorrect email or password")

                self.redis.delete(f"login_fail:{account_id}")

        self.collection.update_one(
            {"_id": account["_id"]},
            {"$set": {"lastLogin": datetime.now(), "login": True}},
        )

        # GET PERMISSION DETAIL
        permissionDetail = {}
        if "permissionId" in account and account["permissionId"]:
            permissionDetail = self.permission_service.get_by_id(
                account["permissionId"]
            )
        user_status = self.user_service.get_user_status_by_id(account["_id"])
        

        return account, permissionDetail, user_status

    def register_google(self, dto: UserDTO):
        account = self.collection.find_one({"email": dto.email})

        if account:
            raise Exception("Your Account Is Already Registered")

        resp = self.user_service.add(dto)

        return resp

    def google_token_exchange(self, token: str):
        userinfo_res = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )

        if userinfo_res.status_code > 299:
            raise Exception("Failed Exchange Token , Token Is Invalid")

        userinfo = userinfo_res.json()

        return userinfo

    def google_exchange_and_get_token(self, token: str):

        userinfo = self.google_token_exchange(token)

        additional_payloads = {}

        try:
            email = userinfo.get("email")
            account, permissionDetail, user_status = (
                self.get_user_properties(
                    AuthDTO(email=email),
                    query={"email": email},
                    validate_password=False,
                )
            )
        except:
            return {
                "registered": False,
                "userInfo": userinfo,
            }

        # single & multi login handling
        multiLogin = account.get("multiLogin", True)
        user_id = account["_id"]
        auth = sign_jwt(
            account["_id"],
            account.get("permissionId", None),
            multiLogin,
            **additional_payloads,
        )

        if multiLogin == False:
            auth_token = auth["token"]
            expire_str = auth["expire"]
            redis_key = f"session:{user_id}"

            redis_client = Services.redis()
            redis_client.delete(redis_key)

            expire_time = datetime.fromisoformat(expire_str)
            current_time = datetime.now(expire_time.tzinfo)
            ttl_seconds = int((expire_time - current_time).total_seconds()) + (
                24 * 60 * 60
            )
            redis_client.setex(redis_key, ttl_seconds, auth_token)

        return {
            "user": {
                "id": user_id,
                "fullname": account["fullname"],
                "username": account["username"],
                "settings": account.get("settings", {}),
                "personalization": account.get("personalization"),
                "email": account["email"],
                "lastOnlineStatus": user_status,
                "permissionId": account.get("permissionId", None),
                "permissionDetail": permissionDetail,
                "groupId": account.get("groupId", None),
                "groupDetail": self.group_service.get_by_id(
                    account.get("groupId", None)
                ),
            },
            "auth": auth,
        }
    def login_by_google(self, dto: GoogleSSORequest):
        code = dto.code
        redirect_uri = dto.redirect_uri

        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_res.status_code > 299:
            raise Exception("Failed Login By Google Please Try Again")

        token = token_res.json()

        userinfo = self.google_token_exchange(token["access_token"])

        additional_payloads = {}

        try:
            email = userinfo.get("email")
            account, permissionDetail, user_status = (
                self.get_user_properties(
                    AuthDTO(email=email),
                    query={"email": email},
                    validate_password=False,
                )
            )
        except Exception as e:
            logger.exception(e)
            return {
                "registered": False,
                "userInfo": userinfo,
            }

        # single & multi login handling
        multiLogin = account.get("multiLogin", True)
        user_id = account["_id"]
        auth = sign_jwt(
            account["_id"],
            account.get("permissionId", None),
            multiLogin,
            **additional_payloads,
        )

        if multiLogin == False:
            auth_token = auth["token"]
            expire_str = auth["expire"]
            redis_key = f"session:{user_id}"

            redis_client = Services.redis()
            redis_client.delete(redis_key)

            expire_time = datetime.fromisoformat(expire_str)
            current_time = datetime.now(expire_time.tzinfo)
            ttl_seconds = int((expire_time - current_time).total_seconds()) + (
                24 * 60 * 60
            )
            redis_client.setex(redis_key, ttl_seconds, auth_token)

        return {
            "user": {
                "id": user_id,
                "fullname": account["fullname"],
                "username": account["username"],
                "personalization": account.get("personalization"),
                "email": account["email"],
                "lastOnlineStatus": user_status,
                "permissionId": account.get("permissionId", None),
                "permissionDetail": permissionDetail,
                "groupId": account.get("groupId", None),
                "groupDetail": self.group_service.get_by_id(
                    account.get("groupId", None)
                ),
            },
            "auth": auth,
        }

    def login(self, dto: AuthDTO):
        get_user_properties_filters = {
            "$or": [
                {"email": dto.email},
                {"username": dto.email},
                {"phone": dto.email},
            ]
        }
        additional_payloads = {}

        if not dto.email:
            raise Exception("User does not exist")

        # Process login by login method
        account,   permissionDetail, user_status = (
            self._process_login_method(dto, get_user_properties_filters)
        )

        # single & multi login handling
        multiLogin = account.get("multiLogin", True)
        user_id = account["_id"]
        auth = sign_jwt(
            account["_id"],
            account.get("permissionId", None),
            multiLogin,
            **additional_payloads,
        )

        if multiLogin == False:
            auth_token = auth["token"]
            expire_str = auth["expire"]
            redis_key = f"session:{user_id}"

            redis_client = Services.redis()
            redis_client.delete(redis_key)

            expire_time = datetime.fromisoformat(expire_str)
            current_time = datetime.now(expire_time.tzinfo)
            ttl_seconds = int((expire_time - current_time).total_seconds()) + (
                24 * 60 * 60
            )
            redis_client.setex(redis_key, ttl_seconds, auth_token)

        return {
            "user": {
                "id": user_id,
                "fullname": account["fullname"],
                "username": account["username"],
                "personalization": account.get("personalization"),
                "settings": account.get("settings", {}),
                "email": account["email"],
                "lastOnlineStatus": user_status,
                "permissionId": account.get("permissionId", None),
                "permissionDetail": permissionDetail,
                "groupId": account.get("groupId", None),
                "groupDetail": self.group_service.get_by_id(
                    account.get("groupId", None)
                ),
                "additional": account.get("additional", None),
            },
            "auth": auth,
        }
    
    def _process_login_method(self, dto: AuthDTO, get_user_properties_filters: dict):
        
        return self.get_user_properties(dto, get_user_properties_filters)


    def _get_user_account_only(self, dto: AuthDTO, query: dict):
        account = self.collection.find_one(query)

        if not account:
            raise Exception(AuthErrors.INCORRECT_CREDENTIALS)

        account_id = account["_id"]
        self.check_account_lock(account_id)
        self._validate_account_status(account)
        try:
            self._validate_password(dto.password, account["password"])
        except:
            self.handle_login_fail(account_id)
            raise Exception(AuthErrors.INCORRECT_CREDENTIALS)

        self.redis.delete(f"login_fail:{account_id}")
        self._update_login_status(account_id)

        return account

    def _validate_account_status(self, account: dict):
        

        # Check expired date
        expired_date = account.get("expiredDate", None)
        if expired_date not in [None, "", 0]:
            current_time = int(datetime.now().timestamp() * 1000)
            if current_time > expired_date:
                raise Exception(AuthErrors.ACCOUNT_EXPIRED)

        # Check account status
        account_status = account.get("status")
        if account_status == "deleted":
            raise Exception(AuthErrors.ACCOUNT_DELETED)
        elif account_status == "blocked":
            raise Exception(AuthErrors.ACCOUNT_BLOCKED)

    def _validate_password(self, input_password: str, stored_password: str):
        if not bcrypt.checkpw(
            input_password.encode("utf-8"), stored_password.encode("utf-8")
        ):
            raise Exception(AuthErrors.INCORRECT_CREDENTIALS)

    def _update_login_status(self, user_id: str):
        self.collection.update_one(
            {"_id": user_id}, {"$set": {"lastLogin": datetime.now(), "login": True}}
        )

    def _get_user_properties(self, account: dict):
        # GET PERMISSION DETAIL
        permissionDetail = {}
        if "permissionId" in account and account["permissionId"]:
            permissionDetail = self.permission_service.get_by_id(
                account["permissionId"]
            )
        user_status = self.user_service.get_user_status_by_id(account["_id"])
        

        return permissionDetail, user_status

    def logout(self, credential: str):
        credential = credential.replace("Bearer ", "")
        decoded_token = decode_jwt(credential, ignoreExpired=True)

        return "Logout Success"

    def validate(self, credential: str, fullResponse: bool = False):
        if not credential:
            raise Exception("Authentication required.")
        credential = credential.replace("Bearer ", "")
        decoded_token = decode_jwt(credential, ignoreExpired=True)

        if fullResponse:
            user_id = decoded_token.get("user_id", None)
            account = self.collection.find_one({"_id": user_id})
            auth = token_response(credential, decoded_token.get("refresh_token"),  decoded_token.get("expire"))
            return self._get_user_properties(account, auth)

        return {"status": "active"}

    def request_change(self, dto: RequestChangeDTO):
            smtp = {
                "smtpEmail": self.smtp_email,
                "smtpHost": self.smtp_host,
                "smtpPort": self.smtp_port,
                "smtpPassword": self.smtp_password,
                "smtpSender": self.smtp_sender,
                "useTls": self.smtp_use_tls,
                "type": self.smtp_type
            }
            account = self.collection.find_one({"email": dto.email})
            if not account:
                raise Exception(f"Account not found")
            else:
                account_id = account["_id"]
                self.check_limit_forgot_password(account_id)
                self.check_forgot_password_cooldown(account_id)
                email_verified = account.get("emailVerified")
                if not email_verified:
                    raise Exception(f"Email not verified. Please contact the administrator.")

                try:
                    mailer_meta = SMTPDTO.model_validate(smtp)
                    mail_handler = MailSender(mailer_meta)
                    new_otp = create_otp()
                    try:
                        mail_handler.connect()

                        self.redis.set(
                            f"email-otp:{md5(new_otp.encode('utf-8')).hexdigest()}",
                            OtpDTO(email=dto.email, otp=new_otp).model_dump_json(),
                            1800,
                        )
                        msg = MIMEMultipart()
                        msg["From"] = mailer_meta.smtpSender or mailer_meta.smtpEmail
                        msg["To"] = dto.email
                        msg["Subject"] = "Permohonan Lupa Password"
                        msg.attach(
                            MIMEText(
                                f"""
Halo {account['fullname']},
Kami menerima permohonan untuk mereset password akun Anda. Jika Anda tidak meminta ini, Anda dapat mengabaikan email ini.

Berikut ini adalah kode keamanan Lupa Password Anda:

{new_otp}

Thanks,
Fusion Team


Jika Anda memiliki pertanyaan atau memerlukan bantuan lebih lanjut, jangan ragu untuk menghubungi kami.
                        """,
                                "plain",
                            )
                        )
                        mail_handler.server.sendmail(
                            from_addr=mailer_meta.smtpSender or mailer_meta.smtpEmail,
                            to_addrs=dto.email,
                            msg=msg.as_string(),
                        )

                        return {"message": "Email request password sent"}

                    except:
                        raise Exception(f"Fail send email request password")
                    finally:
                        mail_handler.close()
                except:
                    raise Exception(
                        f"SMTP of application with email {smtp.smtpEmail} is invalid"
                    )

    def request_verify_email(self,  dto: RequestVerifyEmailDTO):
            smtp = {
                    "smtpEmail": self.smtp_email,
                    "smtpHost": self.smtp_host,
                    "smtpPort": self.smtp_port,
                    "smtpPassword": self.smtp_password,
                    "smtpSender": self.smtp_sender,
                    "useTls": self.smtp_use_tls,
                    "type": self.smtp_type
                }
            account = self.collection.find_one({"email": dto.email})
            if not account:
                raise Exception(f"Account not found")
            else:
                try:
                    mailer_meta = SMTPDTO.model_validate(smtp)
                    mail_handler = MailSender(mailer_meta)
                    token = create_token()
                    verification_url = create_email_link_verification(domain=self.domain, token=token)
                    try:
                        mail_handler.connect()

                        self.redis.set(
                            f"verify-email:{md5(token.encode('utf-8')).hexdigest()}",
                            VerifyEmailDTO(email=dto.email, url=verification_url).model_dump_json(),
                            1800,
                        )
                        msg = MIMEMultipart()
                        msg["From"] = mailer_meta.smtpSender or mailer_meta.smtpEmail
                        msg["To"] = dto.email
                        msg["Subject"] = "Permohonan Verifikasi Alamat Email"
                        msg.attach(
                            MIMEText(
                                f"""
Halo {account['fullname']},
Kami menerima permohonan untuk verifikasi email anda. Jika Anda tidak meminta ini, Anda dapat mengabaikan email ini.

Silakan klik tautan di bawah ini untuk memverifikasi alamat email Anda:

{verification_url}

Thanks,
Fusion Team


Jika Anda memiliki pertanyaan atau memerlukan bantuan lebih lanjut, jangan ragu untuk menghubungi kami.
                        """,
                                "plain",
                            )
                        )
                        mail_handler.server.sendmail(
                            from_addr=mailer_meta.smtpSender or mailer_meta.smtpEmail,
                            to_addrs=dto.email,
                            msg=msg.as_string(),
                        )

                        return {"message": "Email request verify email sent"}

                    except:
                        raise Exception(f"Fail send email request verify email")
                    finally:
                        mail_handler.close()
                except:
                    raise Exception(
                        f"SMTP of application with email {smtp.smtpEmail} is invalid"
                    )

    def verify_email(self, token: str):
        if data_verify_email := self.redis.get(f"verify-email:{md5(token.encode('utf-8')).hexdigest()}"):
            data_verify_email = VerifyEmailDTO.model_validate_json(data_verify_email.encode("utf-8"))
            account = self.collection.find_one({"email": data_verify_email.email})
            if account:
                self.collection.update_one(
                    {"_id": account.get("_id")},
                    {"$set": {"emailVerified": True}},
                )
                account["emailVerified"] = True
                self.redis.delete(
                    f"email-otp:{md5(token.encode('utf-8')).hexdigest()}"
                )
                return account
            else:
                raise Exception("Account is not found!")
        else:
            raise Exception("Token is Invalid or Expired")

    def verity_otp(self, otp: str):
        if self.redis.get(f"email-otp:{md5(otp.encode('utf-8')).hexdigest()}"):
            return {
                "message": "OTP is Valid",
            }
        else:
            raise Exception("OTP is Invalid or Expired")

    def change_password_by_otp(self, dto: ChangePasswordOTPDTO):
        if data_otp := self.redis.get(
            f"email-otp:{md5(dto.otp.encode('utf-8')).hexdigest()}"
        ):
            data_otp = OtpDTO.model_validate_json(data_otp.encode("utf-8"))
            account = self.collection.find_one({"email": data_otp.email})
            if account:
                self.collection.update_one(
                    {"_id": account.get("_id")},
                    {"$set": {"password": encrypt(dto.newPassword)}},
                )
                self.redis.delete(
                    f"email-otp:{md5(dto.otp.encode('utf-8')).hexdigest()}"
                )
                return account
            else:
                raise Exception("Account is not found!")
        else:
            raise Exception("OTP is Invalid or Expired")

    def register(self, dto: RegisterDTO):
            if not settings.AUTH_EMAIL_VERIFICATION:
                return self._register_without_verification(dto)
            smtp = {
                "smtpEmail": self.smtp_email,
                "smtpHost": self.smtp_host,
                "smtpPort": self.smtp_port,
                "smtpPassword": self.smtp_password,
                "smtpSender": self.smtp_sender,
                "useTls": self.smtp_use_tls,
                "type": self.smtp_type
            }
            account = self.collection.find_one({"email": dto.email})
            if account:
                raise Exception(f"Account already exist")
            phone = self.collection.find_one({"phone": dto.phone})
            if phone:
                raise Exception(f"Phone already exist")
            else:
                try:
                    mailer_meta = SMTPDTO.model_validate(smtp)
                    mail_handler = MailSender(mailer_meta)
                    new_otp = create_otp()
                    try:
                        mail_handler.connect()

                        self.redis.set(
                            f"register-otp:{md5(new_otp.encode('utf-8')).hexdigest()}",
                            RegisterOTPDTO(
                                email=dto.email,
                                otp=new_otp,
                                fullname=dto.fullname,
                                username=dto.username,
                                password=dto.password,
                                phone=dto.phone,
                            ).model_dump_json(),
                            1800,
                        )
                        msg = MIMEMultipart()
                        msg["From"] = mailer_meta.smtpSender or mailer_meta.smtpEmail
                        msg["To"] = dto.email
                        msg["Subject"] = "Permohonan Pembuatan Akun Baru"
                        msg.attach(
                            MIMEText(
                                f"""
Halo {dto.fullname},
Kami menerima permohonan untuk membuat akun. Jika Anda tidak meminta ini, Anda dapat mengabaikan email ini.

Ini Berikut adalah kode keamanan permohonan pembuatan akun Anda:

{new_otp}

Thanks,
Fusion Team


Jika Anda memiliki pertanyaan atau memerlukan bantuan lebih lanjut, jangan ragu untuk menghubungi kami.
                        """,
                                "plain",
                            )
                        )
                        mail_handler.server.sendmail(
                            from_addr=mailer_meta.smtpSender or mailer_meta.smtpEmail,
                            to_addrs=dto.email,
                            msg=msg.as_string(),
                        )

                        return {"message": "Email register sent", "verificationRequired": True}
                    except:
                        raise Exception(f"Fail send email register")
                    finally:
                        mail_handler.close()
                except:
                    raise Exception(
                        f"SMTP of application with email {smtp.smtpEmail} is invalid"
                    )

    def _register_without_verification(self, dto: RegisterDTO) -> dict:
        """BE_AUTH_EMAIL_VERIFICATION=false (development only): create the active account at once, no mail."""
        if self.collection.find_one({"email": dto.email}):
            raise Exception("Account already exist")
        if self.collection.find_one({"username": dto.username}):
            raise Exception("Username already exist")
        if self.collection.find_one({"phone": dto.phone}):
            raise Exception("Phone already exist")
        user = self.user_service.add(UserDTO(
            fullname=dto.fullname,
            username=dto.username,
            email=dto.email,
            phone=dto.phone,
            password=dto.password,
            status="active",
            multiLogin=True,
            emailVerified=False,
        ))
        return {"message": "Account created", "verificationRequired": False, "id": user["id"]}

    def verify_register_otp(self, otp: str):
        redis_data = self.redis.get(
            f"register-otp:{md5(otp.encode('utf-8')).hexdigest()}"
        )
        logger.debug(f"Redis: {redis_data}")
        if redis_data:
            redis_data = json.loads(redis_data)
            param_user = UserDTO(
                fullname=redis_data.get("fullname"),
                username=redis_data.get("username"),
                email=redis_data.get("email"),
                phone=redis_data.get("phone"),
                password=redis_data.get("password"),
                status="active",
                multiLogin=True,
                emailVerified=True
            )
            self.user_service.add(param_user)
            return param_user.dict(exclude_unset=True)
        else:
            raise Exception("OTP is Invalid or Expired")

    def refresh(
        self, credential: str, user_id: str,  permission_id: str
    ):
        if isinstance(credential, str):
            credential = credential.replace("Bearer ", "")
        decoded_token = decode_jwt(credential, ignoreExpired=True)

        current_time = time.time()
        expire_time = decoded_token["expire"]
        # refresh_window = 30 * 24 * 60 * 60  # 30 days
        if current_time > expire_time + settings.JWT_REFRESH:
            raise Exception("Token expired more than 30 days ago")

        multiLogin = decoded_token.get("multiLogin", True)
        additional_payload = {
            _key: _val
            for _key, _val in decoded_token.items()
            if _key
            not in [
                "user_id",
                "permission_id",
                "multiLogin",
                "expire",
            ]
        }
        auth = sign_jwt(
            user_id,  permission_id, multiLogin, **additional_payload
        )
        if not multiLogin:
            auth_token = auth["token"]
            expire_str = auth["expire"]

            redis_client = Services.redis()

            redis_key = f"session:{user_id}"
            stored_token = redis_client.get(redis_key)
            if credential != stored_token:
                raise Exception("No active session found for user")

            redis_client.delete(redis_key)
            expire_time = datetime.fromisoformat(expire_str)
            current_time = datetime.now(expire_time.tzinfo)

            ttl_seconds = int((expire_time - current_time).total_seconds()) + (
                24 * 60 * 60
            )
            redis_client.setex(redis_key, ttl_seconds, auth_token)

        self.collection.update_one(
            {"_id": user_id}, {"$set": {"lastLogin": datetime.now(), "login": True}}
        )

        return auth

    def _get_user_properties(self, account: dict, auth: dict):
        permissionDetail, user_status = (
            self._get_user_properties(account)
        )

        multiLogin = account.get("multiLogin", True)
        user_id = account["_id"]

        if multiLogin == False:
            auth_token = auth["token"]
            expire_str = auth["expire"]
            redis_key = f"session:{user_id}"

            redis_client = Services.redis()
            redis_client.delete(redis_key)

            expire_time = datetime.fromisoformat(expire_str)
            current_time = datetime.now(expire_time.tzinfo)
            ttl_seconds = int((expire_time - current_time).total_seconds()) + (
                24 * 60 * 60
            )
            redis_client.setex(redis_key, ttl_seconds, auth_token)

        return {
            "user": {
                "id": user_id,
                "fullname": account["fullname"],
                "username": account["username"],
                "personalization": account.get("personalization"),
                "email": account["email"],
                "lastOnlineStatus": user_status,
                "permissionId": account.get("permissionId", None),
                "permissionDetail": permissionDetail,
                "groupId": account.get("groupId", None),
                "groupDetail": self.group_service.get_by_id(
                    account.get("groupId", None)
                ),
            },
            "auth": auth,
        }


import pyotp
import qrcode 
import io
import base64       
class TwoFactorService:
    def __init__(self):
        self.mongo = Services.mongo()
        self.redis = Services.redis()
        self.collection_user = self.mongo[settings.MONGO_DB][settings.MONGO_COLLECTION_USER]

    def _generate_qr_logic(self, user_id: str, email: str):
        user = self.collection_user.find_one({"_id": user_id})
        two_factor_secret = user.get("two_factor_secret", "")
        if two_factor_secret:
            signature_key = two_factor_secret
        else:
            signature_key = pyotp.random_base32()
            self.redis.set(
                f"2fa-sign:{user_id}",
                signature_key,
                1800
            )

        uri = pyotp.totp.TOTP(signature_key).provisioning_uri(
            name=email, 
            issuer_name='Fusion'
        )

        img = qrcode.make(uri)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return {
            "qr_image_base64": img_str,
            "secret_manual": signature_key,
            "message": "Scan QR, then inout OTP in Verify menu."
        }

    def generate_qr_for_user(self, credential: str):
        token = credential.replace("Bearer ", "")
        decoded_token = decode_jwt(token, ignoreExpired=True)
        user_id = decoded_token["user_id"]
        user = self.collection_user.find_one({"_id": user_id})
        return self._generate_qr_logic(user_id, user["email"])

    def _send_email_otp(self, email: str, otp: str):
        smtp = {
                "smtpEmail": self.smtp_email,
                "smtpHost": self.smtp_host,
                "smtpPort": self.smtp_port,
                "smtpPassword": self.smtp_password,
                "smtpSender": self.smtp_sender,
                "useTls": self.smtp_use_tls,
                "type": self.smtp_type
            }
            
        mailer_meta = SMTPDTO.model_validate(smtp)
        mail_handler = MailSender(mailer_meta)
        
        try:
            mail_handler.connect()
            
            # Send Email
            msg = MIMEMultipart()
            msg["From"] = mailer_meta.smtpSender
            msg["To"] = email
            msg["Subject"] = "2FA Verification Code"
            
            body = f"Your verification code is: {otp}"
            msg.attach(MIMEText(body, "plain"))
            
            mail_handler.server.send_message(msg)
            mail_handler.close()
        except Exception as e:
            if 'mail_handler' in locals():
                mail_handler.close()
            raise Exception(f"Failed to send email: {str(e)}")

    def generate_2fa(self, dto: GenerateTwoFactorDTO):
        from service.auth import Auth
        auth_service = Auth()

        login_dto = AuthDTO(email=dto.email, password=dto.password)
        query = {
            "$or": [
                {"email": dto.email},
                {"username": dto.email},
                {"phone": dto.email},
            ]
        }

        try:
            account, _, _, _, _ = auth_service.get_user_properties(login_dto, query, validate_password=True)
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
        user_id = account["_id"]
        session_token = create_token()
        
        session_data = {
            "user_id": user_id,
            "email": account["email"],
            "type": dto.type,
            "otp": "",
            "resend_count": 0
        }

        if dto.type == "email":
            new_otp = create_otp()
            session_data["otp"] = new_otp
            
            self._send_email_otp(account["email"], new_otp)
            
            self.redis.set(f"2fa-session:{session_token}", json.dumps(session_data), ex=300)
            
            return {
                "session_token": session_token,
                "message": "Verification code sent to your email."
            }
                
        elif dto.type == "google_authenticator":
            qr_result = self._generate_qr_logic(user_id, account["email"])
            self.redis.set(f"2fa-session:{session_token}", json.dumps(session_data), ex=300)
            
            return {
                "session_token": session_token,
                **qr_result
            }
        else:
            raise Exception(f"Unsupported 2FA type: {dto.type}")

    def verify_two_factor(self, dto: TwoFactorVerifyDTO):
        session_json = self.redis.get(f"2fa-session:{dto.session_token}")
        if not session_json:
            raise Exception("Session expired or invalid. Please request a new 2FA code.")
            
        session = json.loads(session_json)
        user_id = session["user_id"]
        otp = dto.otp

        # 1. Check Email OTP
        if session["type"] == "email":
            if session["otp"] == otp:
                self.redis.delete(f"2fa-session:{dto.session_token}")
            else:
                raise Exception("Wrong OTP Code")

        # 2. Check Google Authenticator
        elif session["type"] == "google_authenticator":
            # Check for Setup Mode first
            temp_secret_from_redis = self.redis.get(f"2fa-sign:{user_id}")
            if temp_secret_from_redis:
                if isinstance(temp_secret_from_redis, bytes):
                    temp_secret_from_redis = temp_secret_from_redis.decode("utf-8")
                
                totp = pyotp.TOTP(temp_secret_from_redis)
                if totp.verify(otp, valid_window=1):
                    self.collection_user.update_one({"_id": user_id}, {"$set": {"two_factor_secret": temp_secret_from_redis}})
                    self.redis.delete(f"2fa-sign:{user_id}")
                    self.redis.delete(f"2fa-session:{dto.session_token}")
                else:
                    raise Exception("Wrong OTP Code")
            else:
                # Login Mode
                user = self.collection_user.find_one({"_id": user_id})
                db_secret_mongo = user.get("two_factor_secret", "")

                if db_secret_mongo:
                    totp = pyotp.TOTP(db_secret_mongo)
                    if totp.verify(otp, valid_window=1):
                        self.redis.delete(f"2fa-session:{dto.session_token}")
                    else:
                        raise Exception("Wrong OTP Code")
                else:
                    raise Exception("User not activated 2FA yet.")
        else:
             raise Exception(f"Unsupported 2FA type: {session['type']}")

        # Success - Generate Full Login Response
        account = self.collection_user.find_one({"_id": user_id})
        
        # Build token and user info
        multiLogin = account.get("multiLogin", True)
        auth = sign_jwt(
            account["_id"],
            account.get("permissionId", None),
            multiLogin,
        )

        return {
            "status": "true",
            "message": "Login Granted",
            "user": {
                "id": user_id,
                "fullname": account["fullname"],
                "username": account["username"],
                "email": account["email"],
                "permissionId": account.get("permissionId", None),
            },
            "auth": auth,
        }

    def resend_2fa(self, dto: TwoFactorResendDTO):
        session_json = self.redis.get(f"2fa-session:{dto.session_token}")
        if not session_json:
            raise Exception("Session expired or invalid. Please request a new 2FA code.")
            
        session = json.loads(session_json)
        
        if session["resend_count"] >= 5:
            raise Exception("Resend limit reached. Please start a new 2FA request.")
            
        if session["type"] == "email":
            new_otp = create_otp()
            session["otp"] = new_otp
            session["resend_count"] += 1
            
            # Update Redis
            self.redis.set(f"2fa-session:{dto.session_token}", json.dumps(session), ex=300)
            
            # Send Email
            self._send_email_otp(session["email"], new_otp)
            
            return {"message": "Verification code has been resent to your email."}
        else:
            raise Exception("Resend not supported for this 2FA type.")
