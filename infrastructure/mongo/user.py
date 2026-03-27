from typing import Optional

from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.user import UserEntity
from domain.repositories.user import IUserRepository


class UserRepository(IUserRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def basic_sign_in(self, name: str) -> UserEntity:
        result = await self.collection.insert_one(
            {"name": name, "favorite_property_ids": []}
        )
        return UserEntity(
            _id=result.inserted_id,
            name=name,
            source="basic",
            favorite_property_ids=[],
        )

    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]:
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if doc:
            return UserEntity(**doc)
        return None

    async def update_user_profile(self, user_id: str, name: str) -> UserEntity:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": name}}
        )
        return await self.get_user_by_id(user_id)

    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ) -> UserEntity:
        operator = "$addToSet" if is_favorite else "$pull"
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {operator: {"favorite_property_ids": str(property_id)}},
        )
        return await self.get_user_by_id(user_id)
