# -*- coding: utf-8 -*-
import json
from config.base import settings
from loguru import logger
from datetime import datetime
from service import Services
from service import BaseMongoRepository
from service import change_field_id
from dto.permission import PermissionDTO, UpdatePermissionDTO
from util.helper import mongo_query_builder, get_md5


class Permission(BaseMongoRepository):
    def __init__(self):
        super().__init__()

        self.mongo = Services.mongo()
        self.collection = self.get_collection(settings.MONGO_COLLECTION_PERMISSION)
        self.collection_view = self.get_collection(
            f"v_{settings.MONGO_COLLECTION_PERMISSION}"
        )

    def add(self, dto: PermissionDTO):
        _id = get_md5(json.dumps(dto.dict()))
        data = self.get_by_id(_id)
        if not data:
            data = dto.dict()
            data["createdAt"] = datetime.now()
            return self.add_or_update_process(data, _id)
        else:
            logger.info(f"Permission already exist")
            raise Exception(f"data permission already exist!")

    def update(self, dto: UpdatePermissionDTO):
        data = self.get_by_id(dto.id)
        if data:
            return self.add_or_update_process(dto.dict(), dto.id)
        else:
            return f"There is no data with id: {dto.id}"

    def update_partial(self, dto: UpdatePermissionDTO):
        data = self.get_by_id(dto.id)
        if data:
            dto_dump = dto.model_dump(exclude_defaults=True)
            update_privileges = None
            if dto_dump.get("privileges", None) is not None:
                update_privileges = dto_dump.pop("privileges")
            data.update(dto_dump)
            privileges = data.get("privileges", None)
            if privileges is not None and update_privileges is not None:
                for item in update_privileges:
                    if item.get("id", None) is None:
                        continue
                    index = next(
                        (i for i, d in enumerate(privileges) if d["id"] == item["id"]),
                        None,
                    )
                    if index is not None:
                        privileges[index] = item
                    else:
                        privileges.append(item)
                data["privileges"] = privileges
            return self.add_or_update_process(data, dto.id)
        else:
            return f"There is no data with id: {dto.id}"

    def get_by_id(self, _id):
        data = self.collection_view.find_one({"_id": _id})
        if data:
            data["id"] = data.pop("_id")
            return data
        return {}

    def add_or_update_process(self, data, _id):
        if "id" in data:
            data.pop("id")

        data["updatedAt"] = datetime.now()
        self.collection.update_one({"_id": _id}, {"$set": data}, upsert=True)
        logger.success(f"{_id} has been inserted.")

        data["id"] = _id
        return data

    def delete(self, _id):
        self.collection.delete_one({"_id": _id})
        return f"{_id} has been deleted."

    def get_all(self, dto):
        query = mongo_query_builder(dto, text_type="name,description")
        data = (
            self.collection_view.find(query)
            .skip((dto.page - 1) * dto.size)
            .limit(dto.size)
            .sort(dto.orderBy, -1 if dto.order.lower() == "desc" else 1)
        )

        return change_field_id(list(data)), self.collection.count_documents(query)
