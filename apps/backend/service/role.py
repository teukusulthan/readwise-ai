# -*- coding: utf-8 -*-
import json
from config.base import settings
from loguru import logger
from service import BaseMongoRepository
from datetime import datetime
from service import Services
from service import change_field_id
from dto.role import RoleDTO, UpdateRoleDTO
from util.helper import mongo_query_builder, get_md5


class Role(BaseMongoRepository):
    def __init__(self):
        super().__init__()
        self.mongo = Services.mongo()
        self.collection = self.get_collection(settings.MONGO_COLLECTION_ROLE)

    def add(self, dto: RoleDTO):
        _id = get_md5(json.dumps(dto.dict()))
        data = self.get_by_id(_id)
        if not data:
            data = dto.dict()
            data["createdAt"] = datetime.now()
            return self.add_or_update_process(data, _id)
        else:
            logger.info(f"Role already exist")
            raise Exception(f"data role already exist!")

    def update(self, dto: UpdateRoleDTO):
        data = self.get_by_id(dto.id)
        if data:
            return self.add_or_update_process(dto.dict(), dto.id)
        else:
            return f"There is no data with id: {dto.id}"

    def get_by_id(self, _id):
        data = self.collection.find_one({"_id": _id})
        if data:
            data["id"] = data.pop("_id")
            return data
        return {}

    def add_or_update_process(self, data, _id):
        if "id" in data:
            data.pop("id")

        data["updatedAt"] = datetime.now()
        self.collection.update_one({'_id': _id}, {"$set": data}, upsert=True)
        logger.success(f"{_id} has been inserted.")

        data["id"] = _id
        return data

    def delete(self, _id):
        self.collection.delete_one({"_id": _id})
        return f"{_id} has been deleted."

    def get_all(self, dto):
        query = mongo_query_builder(dto, text_type="name,description")
        data = self.collection.find(query).skip((dto.page - 1) * dto.size).limit(dto.size).sort(
            dto.orderBy, -1 if dto.order.lower() == "desc" else 1)

        return change_field_id(list(data)), self.collection.count_documents(query)
