# -*- coding: utf-8 -*-
import bcrypt
import jmespath
from service import BaseMongoRepository


from config.base import settings
from util.helper import encrypt, censor_email
from loguru import logger
from datetime import datetime, timedelta
from service import Services
from dto.user import (
    UserDTO,
    UpdateUserDTO,
    ResetPasswordDTO,
    FindUserDTO,
)
from util.helper import mongo_query_builder, get_md5
from typing import Literal


ADMIN_AND_OWNER_PERMISSIONS = [
    "admin",
    "owner"
]


class User(BaseMongoRepository):
    def __init__(self):
        super().__init__()

        self.mongo = Services.mongo()
        self.collection = self.get_collection(settings.MONGO_COLLECTION_USER)
        self.collection_group = self.get_collection(settings.MONGO_COLLECTION_GROUP)

        self.collection_view = self.get_collection(
            f"v_{settings.MONGO_COLLECTION_USER}"
        )
        
    def add(self, dto: UserDTO, password_is_hash: bool = False):
        """`password_is_hash`: dto.password is already a bcrypt hash (a registration confirmed by email code)."""
        _id = get_md5(f"{dto.email}-{dto.phone}")
        data = self.get_by_id(_id)
        if not data:
            data = dto.dict()
            data["createdAt"] = datetime.now()
            return self.add_or_update_process(data, _id, password_is_hash=password_is_hash)
        else:
            logger.info(f"User already exist")
            raise Exception(f"User already exist!")

    def update(self, dto: UpdateUserDTO):
        data = self.get_by_id(dto.id)
        if data:
            param_update = UpdateUserDTO(**data).dict()
            dto_dict = {k: v for k, v in dto.dict().items() if v is not None}
            param_update.update(dto_dict)

            if dto_dict.get("password") is None:
                param_update["password"] = None

            if dto_dict.get("email") is None:
                param_update["email"] = None

            return self.add_or_update_process(param_update, dto.id)
        else:
            return f"There is no data with id: {dto.id}"

    def update_profile(self, dto: UpdateUserDTO):
        data = self.get_by_id(dto.id)
        if data:
            param_update = UpdateUserDTO(**data).dict()
            dto_dict = {k: v for k, v in dto.dict().items() if v is not None}
            param_update.update(dto_dict)

            if dto_dict.get("password") is None:
                param_update["password"] = None

            if dto_dict.get("email") is None:
                param_update["email"] = None

            return self.add_or_update_process(param_update, dto.id)

        else:
            return f"There is no data with id: {dto.id}"

    
    def get_by_id(self, _id):
        data = self.collection.find_one({"_id": _id})
        if data:
            group_id = data.get("groupId")
            group_id = [group_id] if group_id else []

            data["email"] = censor_email(data["email"])
            data["password"] = "##########"
            data["id"] = data.pop("_id")
            
            return data
        return {}

    def get_one(self, id: str):
        data = self.collection_view.find_one({"_id": id})
        if data:
            data["id"] = data.pop("_id")
            return data
        return {}

    def get_one_by_username(self, username: str):
        data = self.collection_view.find_one({"username": username})
        if data:
            data["id"] = data.pop("_id")
            return data
        return {}


    def check_unique(self, check_field: Literal["email", "username", "phone"], value):
        data = self.collection.find_one({check_field: value})
        if data:
            return {
                "status": True,
            }
        return {
            "status": False,
        }

    def reset_password(self, dto: ResetPasswordDTO):
        data = self.collection.find_one({"_id": dto.id})
        if data:
            self.collection.update_one(
                {"_id": dto.id}, {"$set": {"password": encrypt(dto.password)}}
            )
            return data
        else:
            raise Exception("Account is not found!")

    def add_or_update_process(self, data, _id, password_is_hash: bool = False):
        if "id" in data:
            method = "put"
            endpoint = "api/v1/appUsers/update"
            data.pop("id")
            data.pop("password")
            if "email" in data and not data["email"]:
                old_account = self.collection.find_one({"_id": _id})
                data["email"] = old_account["email"]
            else:
                query_mongo = [{"email": data["email"]}, {"username": data["username"]}]
                if data["phone"]:
                    query_mongo.append({"phone": data["phone"]})
                match_email_account = self.collection.find_one(
                    {"$and": [{"$or": query_mongo}, {"_id": {"$ne": _id}}]}
                )
                if match_email_account:
                    raise Exception("Email, Username or Phone already exists!")
        else:
            method = "post"
            endpoint = "api/v1/appUsers/add"

            if not password_is_hash:
                data["password"] = encrypt(data["password"])

        data["updatedAt"] = datetime.now()
        self.collection.update_one(
            {"_id": _id},
            {"$set": data},
            upsert=True,
        )
        logger.success(f"{_id} has been inserted.")

        if data.get("email"):
            data["email"] = censor_email(data["email"])

        data["password"] = "##########"
        data["id"] = _id
        return data

    def delete(self, _id):
        self.collection.delete_one({"_id": _id})
        
        return f"{_id} has been deleted."

    def get_all(self, dto: FindUserDTO):
        query = mongo_query_builder(
            dto, text_type="username,fullname,email", additional_ignore="online"
        )
        if dto.online:
            if "$and" not in query:
                query["$and"] = []
            query["$and"].append(
                {
                    "userStatus.lastActive": {
                        "$gte": datetime.now() - timedelta(minutes=5)
                    }
                }
            )
        data = (
            self.collection_view.find(query)
            .skip((dto.page - 1) * dto.size)
            .limit(dto.size)
            .sort(dto.orderBy, -1 if dto.order.lower() == "desc" else 1)
        )

        data = list(data)

        result = []
        for datum in data:
            datum["id"] = datum.pop("_id")
            result.append(datum)

        return result, self.collection_view.count_documents(query)

    # * ================== USER STATUS ==================
    def set_user_status(self, dto):
        if dto.id is None:
            raise Exception("id cannot be null !")

        data = dto.dict()
        data["createdAt"] = datetime.now()
        data["lastActive"] = datetime.now()
        return self.add_or_update_user_status_process(data, dto.id)

    def get_user_status_by_id(self, id: str):
        # Online status is not tracked in this project: the boilerplate's status collection was never
        # configured (no MONGO_COLLECTION_* for it), and reading it made every login fail.
        return {}

    def add_or_update_user_status_process(self, data, _id):
        if "id" in data:
            data.pop("id")

        data["updatedAt"] = datetime.now()
        self.collection_user_status.update_one(
            {"_id": _id}, {"$set": data}, upsert=True
        )
        logger.success(f"{_id} has been inserted.")

        data["id"] = _id
        return data


    def add_or_update_process_col(self, col, data, _id):
        if "id" in data:
            data.pop("id")

        data["updatedAt"] = datetime.now()
        col.update_one({"_id": _id}, {"$set": data}, upsert=True)
        logger.success(f"{_id} has been inserted.")

        data["id"] = _id
        return data
