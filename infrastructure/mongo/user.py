from datetime import UTC, datetime
from typing import Optional

from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.user import UserEntity, UserSearchRecord
from domain.repositories.user import IUserRepository

RECENT_SEARCH_LIMIT = 20


class UserRepository(IUserRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def basic_sign_in(self, name: str, pet_name: str | None = None) -> UserEntity:
        result = await self.collection.insert_one(
            {
                "name": name,
                "pet_name": pet_name,
                "favorite_property_ids": [],
                "recent_searches": [],
            }
        )
        return UserEntity(
            _id=result.inserted_id,
            name=name,
            pet_name=pet_name,
            source="basic",
            favorite_property_ids=[],
            recent_searches=[],
        )

    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]:
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if doc:
            return UserEntity(**doc)
        return None

    async def update_user_profile(self, user_id: str, name: str) -> UserEntity:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"name": name}}
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

    async def record_recent_search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = RECENT_SEARCH_LIMIT,
    ) -> UserEntity:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None

        normalized_query = query.strip()
        records = [
            record
            for record in user.recent_searches
            if record.query.strip() != normalized_query
        ]
        records.insert(
            0,
            UserSearchRecord(
                query=normalized_query,
                searched_at=datetime.now(UTC),
            ),
        )
        trimmed_records = records[: max(1, min(limit, 50))]

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "recent_searches": [
                        record.model_dump(mode="json") for record in trimmed_records
                    ],
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return await self.get_user_by_id(user_id)
